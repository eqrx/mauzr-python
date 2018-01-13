mauzr
=====

![](https://img.shields.io/travis/eqrx/mauzr.svg)
![](https://img.shields.io/codeclimate/maintainability/eqrx/mauzr.svg)

Mauzr is a hardware focussed multi-agent framework written in Python and C.
It is intended to aid in the implementation of IoT applications, smart environments
and cyber-physical systems (or whatever else the latest buzzword may be ;)
The primary difference to other IoT-Frameworks is the use of *distributed drivers*:
As much of the logic governing the embedded devices and their peripherals as
possible is located in networked agents (rather than the device itself).
This allows for an easier integration with high-level  programming languages
and other frameworks.

Motivation
----------
I like to develop smart environments and spend a lot of my time doing so.
When I also started to write my master thesis on a similar topic, I realised
that I could save a lot of time merging some of my projects into a development
framework to simplify creation of new agents.
I personally dislike the assumption that a network can be "*isolated and
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
your installation anyway. I check and sign every version tag in this repository
so you can use `git verify-tag` to inspect if the tag originated from me.

- Receive the signing key:
  `gpg --recv-keys 0CDDE5DB`
- VERIFY KEY CAREFULLY!
  (Fingerprint: F2BD C496 45AB 1587 B6CC 280D 2ED5 9137 0CDD E5DB)
- Clone and enter the repository:
  `git clone https://github.com/eqrx/mauzr.git && cd mauzr`
- Verify commit history
- Install with pip:
  `pip3 install -U .`

How to contribute
-----------------

If you like to contribute (which would make me happy :)) you may participate
in the issue tracker and/or open pull requests.
