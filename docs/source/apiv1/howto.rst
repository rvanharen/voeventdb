.. _apiv1_howto:

Querying the REST API
=====================
The voeventdb web-interface is designed around widely used RESTful_ concepts,
which means (simplifying grossly) that all the details of your data query are
encoded in an HTTP URL. By making requests at that URL, you get back the data
matching your query. You can try this out by following links and editing the URL
in your browser, but typically you'll want to grab data using a scripting
library such as Python's requests_. [#client]_

.. [#client] A ready-made Python-client library which wraps requests_ in a
    convenient fashion can be found at
    https://github.com/timstaley/voeventdb.remote.

.. _RESTful: https://en.wikipedia.org/wiki/Representational_state_transfer
.. _JSON: https://en.wikipedia.org/wiki/JSON
.. _requests: http://docs.python-requests.org/


Finding and using endpoints
----------------------------

The base URLs which represent different queries are known as endpoints -
full listings for voeventdb can be found on the
:ref:`apiv1_endpoints` page.
Some useful places to start are the
`root <endpoints.html#get--apiv1->`_ endpoint, which provides a concise listing
of the endpoints available, and the
`stream count <endpoints.html#get--apiv1-map-stream_count>`_ endpoint, which
serves as a sort of 'contents' page for the database.


.. _narrowing:

Narrowing your query
--------------------

By default, most endpoints return data on *all* VOEvents
currently stored in the database. [#notalldata]_
To narrow down your query to a specific subset of the VOEvents,
you can apply a selection of the available filters listed on the
:ref:`apiv1_filters` page.
Filters are applied by adding key-value pairs as part of the
`query-string`_ in your HTTP request.

For example, to return a count of the
packets stored since the start of November 2015, which have been assigned the
'observation' role, you can form an HTTP address like:

http://voeventdb.4pisky.org/apiv1/count?authored_since=2015-11&role=observation

Though typically you would let your scripting library do the job of stitching
together the various parts. See the :ref:`apiv1_filters` page for more details.

.. note::

    You can apply any filter (or combination of filters) to any endpoint, so
    (for example)

    http://voeventdb.4pisky.org/apiv1/map/stream_count?authored_since=2015-11&role=observation

    is also a valid query-URL (where we have replaced the ``/apiv1/count``
    endpoint with ``/apiv1/map/stream_count``).





.. [#notalldata] The exceptions are the
    :ref:`single-packet endpoints<apiv1_packet_endpoints>`:,
    which are intended to retrieve data pertaining to a single VOEvent.


.. _query-string: https://en.wikipedia.org/wiki/Query_string
.. _curl: http://curl.haxx.se/


.. _url-encoding:

URL-Encoding
-------------

Note that if you are accessing the
:ref:`single-packet endpoints<apiv1_packet_endpoints>`:,
or specifying a query-filter value which contains the ``#``
character, then you will need to use `URL-encoding <URL-encode_>`_ (because otherwise the
query-value is indistinguishable from an incorrectly-formed URL). It's simple to
URL-encode the value using a `web-based tool`_, or e.g. in
Python::

    import urllib
    s = urllib.quote_plus("ivo://foo.bar/baz#quux")
    print(s)


.. _URL-encode: https://en.wikipedia.org/wiki/Query_string#URL_encoding
.. _web-based tool: http://meyerweb.com/eric/tools/dencoder/


.. _pagination:

List-pagination controls
----------------------------
The database can easily handle millions of entries, so it makes sense to
break up the return-data for queries which return lists
of data. You can use pagination-keys in the same manner as
query-keys (i.e. in the query-string) to control this:


.. autoclass:: voeventdb.server.restapi.v1.definitions.PaginationKeys
    :members:
    :undoc-members:

.. _ordervalues:

.. autoclass:: voeventdb.server.restapi.v1.definitions.OrderValues
    :members:
    :undoc-members:

.. _returned-content:

Returned content
----------------
.. autoclass:: voeventdb.server.restapi.v1.viewbase.ResultKeys
    :members:
    :undoc-members: