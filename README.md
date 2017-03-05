mauzr
=====

Mauzr is a hardware focussed multi-agent framework written in python. You can
implement your own smart environment or cyber-physical system with help
of this project.

Motivation
----------

I like to develop smart environments and spend a lot of my time doing so.
When I also started to write my master thesis on a similar topic, I realised
I can save a lot of time merging some of my projects into a development
framework to simplify creation of new agents.
Personally I dislike the assumption that a network can be "*isolated and
secure*", so the framework needs to be secure, robust and reliable.

Documentation
-------------

The documentation can be found at
[http://mauzr.eqrx.net](http://mauzr.eqrx.net).

License
-------

All contents of this project are licensed under the
GNU Affero General Public License Version 3. See LICENSE file for the full
license.

Installing
----------

If you like to use this package right away just install it with
`pip3 install mauzr`.

How to contribute
-----------------

If you like to contribute (which would make me happy :)) you may participate
in the issue tracker and/or open pull requests. 

Versioning
----------

This project uses version tags. A version tag is a tag with a name in the form
of vYYMMDD.N, specifying the date of the release and release number of the day.
The `setup.py` script parses this information into the version scheme
YYMMDD.N-post<No. of commits after tag>.
