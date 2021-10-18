#!/bin/bash
set -ev

docker pull zebralucky/electrum-cintamani-winebuild:Linux40x

docker pull zebralucky/electrum-cintamani-winebuild:AppImage40x

docker pull zebralucky/electrum-cintamani-winebuild:Wine41x
