# To rebuild all gds

Build notes are also in the tt-02-build of discord

On git tag tapeout

run 

    . setuptokens.sh
    ./configure.py --harden

Some projects will fail with golden config. Change this line in golden config

    set ::env(PL_BASIC_PLACEMENT) {1}

Then reharden the fails:

    for i in 000 027 047 062 064 081 087 092 094 117 118 126 129 140 141 146 153 156 163 165 ; do 
        echo $i
        ./configure.py  --single $i --harden
    done

Project 106 only hardens with the config.tcl as provided

After rehardening, this should return empty:

    grep 'Flow failed' projects/*/runs/wokwi/errors.log

