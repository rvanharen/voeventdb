from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (backref, deferred, relationship,
                            )
from sqlalchemy import Column, ForeignKey
import sqlalchemy as sql
import voeventparse as vp
from datetime import datetime
import iso8601
import pytz
from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)

Base = declarative_base()


def _grab_xpath(root, xpath, converter=lambda x: x):
    """
    XML convenience - grabs the first element at xpath if present, else returns None.
    """
    elements = root.xpath(xpath)
    if elements:
        return converter(str(elements[0]))
    else:
        return None

class OdictMixin(object):
    def to_odict(self):
        """
        Returns an OrderedDict representation of the SQLalchemy table row.
        """
        colnames = [c.name for c in self.__table__.columns]
        return OrderedDict(((col, getattr(self, col)) for col in colnames))


class Voevent(Base, OdictMixin):
    """
    Define the core VOEvent table.

    .. NOTE::
        On datetimes:
        We store datetimes 'with timezone' even though we'll use the convention
        of storing UTC throughout (and VOEvents are UTC too).
        This helps to make explicit what convention we're using and avoid
        any possible timezone-naive mixups down the line.

        However, if this ever gets used at (really large!) scale, then may
        need to be wary of issues with partitioning really large datasets, cf:
        http://justatheory.com/computers/databases/postgresql/use-timestamptz.html
        http://www.postgresql.org/docs/9.1/static/ddl-partitioning.html

    """
    __tablename__ = 'voevent'
    # Basics: Attributes or associated metadata present for almost every VOEvent:
    id = Column(sql.Integer, primary_key=True)
    received = Column(
        sql.DateTime(timezone=True), nullable=False,
        doc="Records when the packet was loaded into the database"
    )
    ivorn = Column(sql.String, nullable=False, unique=True, index=True)
    stream = Column(sql.String, index=True)
    role = Column(sql.Enum(vp.definitions.roles.observation,
                           vp.definitions.roles.prediction,
                           vp.definitions.roles.utility,
                           vp.definitions.roles.test,
                           name="roles_enum",
                           ),
                  index=True
                  )
    version = Column(sql.String)
    # Who
    author_ivorn = Column(sql.String)
    author_datetime = Column(sql.DateTime(timezone=True))
    # Finally, the raw XML. Mark this for lazy-loading, cf:
    # http://docs.sqlalchemy.org/en/latest/orm/loading_columns.html
    xml = deferred(Column(sql.String))

    cites = relationship("Cite", backref=backref('voevent', order_by=id),
                         cascade="all, delete, delete-orphan")

    @staticmethod
    def from_etree(root, received=pytz.UTC.localize(datetime.utcnow())):
        """
        Init a Voevent row from an LXML etree loaded with voevent-parse
        """
        ivorn = root.attrib['ivorn']
        # Stream- Everything except before the '#' separator,
        # with the prefix 'ivo://' removed:
        stream = ivorn.split('#')[0][6:]
        row = Voevent(ivorn=ivorn,
                      role=root.attrib['role'],
                      version=root.attrib['version'],
                      stream=stream,
                      xml=vp.dumps(root),
                      received=received,
                      )
        row.author_datetime = _grab_xpath(root, 'Who/Date',
                                          converter=iso8601.parse_date)
        row.author_ivorn = _grab_xpath(root, 'Who/AuthorIVORN')

        row.cites = Cite.from_etree(root)
        return row



    def _reformatted_prettydict(self, valformat=str):
        pd = self.prettydict()
        return '\n'.join(
            ("{}={}".format(k, valformat(v)) for k, v in pd.iteritems()))

    def __repr__(self):
        od = self.to_odict()
        content = ',\n'.join(
            ("{}={}".format(k, repr(v)) for k, v in od.iteritems()))
        return """<Voevent({})>""".format(content)

    def __str__(self):
        od = self.to_odict()
        od.pop('xml')
        content = ',\n    '.join(
            ("{}={}".format(k, str(v)) for k, v in od.iteritems()))
        return """<Voevent({})>""".format(content)


class Cite(Base, OdictMixin):
    """
    Record the citations given by each VOEvent.

    Relationship is one Voevent -> Many Cites.

    This is quite inefficient (e.g. in the case that the IVORN is known to the
    database, and is cited by many Voevents) but necessary, since we may see an
    IVORN cited which is not present. If this becomes an issue, I can imagine
    various schemes where e.g. a Voevent is created with just a bare IVORN and
    no other data if it's cited but not ingested, with a flag-bit set
    accordingly. Or we could create a separate 'cited IVORNS' table. But
    probably you ain't gonna need it.

    (P.S. Yes, cite is a valid noun form in addition to verb:
    http://www.grammarphobia.com/blog/2011/10/cite.html
    And it's much shorter than 'citation'.)

    Note that technically there's a slight model mismatch here: What we're
    really modelling are the EventIVORN entries in the Citations section
    of the VOEvent, which typically share a description between them.
    This may result in duplicated descriptions. Meh.

    """
    __tablename__ = 'cite'
    id = Column(sql.Integer, primary_key=True)
    voevent_id = Column(sql.Integer, ForeignKey(Voevent.id))
    ref_ivorn = Column(sql.String, nullable=False, index=True)
    cite_type = Column(sql.Enum(vp.definitions.cite_types.followup,
                                vp.definitions.cite_types.retraction,
                                vp.definitions.cite_types.supersedes,
                                name="cite_types_enum",
                                ),
                       nullable=False
                       )
    description = Column(sql.String)


    @staticmethod
    def from_etree(root):
        """
        Load up the citations, if present, for initializing with the Voevent.
        """
        cite_list = []
        citations = root.xpath('Citations/EventIVORN')
        if citations:
            description = root.xpath('Citations/Description')
            if description:
                description_text = description[0].text
            else:
                description_text = None
            for entry in root.Citations.EventIVORN:
                if entry.text:
                    cite_list.append(
                        Cite(ref_ivorn=entry.text,
                             cite_type=entry.attrib['cite'],
                             description=description_text)
                    )
                else:
                    logger.info(
                        'Ignoring empty citation in {}'.format(
                            root.attrib['ivorn']))
        return cite_list

    def __repr__(self):
        od = self.to_odict()
        content = ',\n'.join(
            ("{}={}".format(k, repr(v)) for k, v in od.iteritems()))
        return """<Cite({})>""".format(content)
