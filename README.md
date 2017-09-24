mauzr
=====

![](https://img.shields.io/travis/mauzr/pat-mauzr.svg?maxAge=2592000)
![](https://img.shields.io/github/tag/mauzr/pat-mauzr.svg?maxAge=2592000)

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

Pip does not support package signatures. With some extra steps you can verify
your installation anyways. I check and sign every version tag in this repository
so you can use `git verify-tag` to inspect if the tag originated from me.

- Receive the signing key:
  `gpg --recv-keys 0CDDE5DB`
- VERIFY KEY CAREFULLY
  (Fingerprint: F2BD C496 45AB 1587 B6CC 280D 2ED5 9137 0CDD E5DB)
- Clone and enter the repository:
  `git clone https://github.com/eqrx/mauzr.git && cd mauzr`
- Find latest tag, check it out and verify it:
  `t=$(git tag -l 'v*.*'|tail -1) && git checkout $t && git verify-tag $t`
- Install with pip:
  `pip3 install -U .`

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
