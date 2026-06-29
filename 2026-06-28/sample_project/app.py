#!/usr/bin/env python3
"""Tiny sample file with a few annotation comments for demo purposes."""


def load_config(path):
    # TODO: support YAML config files
    with open(path) as fh:
        return fh.read()


def parse(data):
    # FIXME(sayed): this breaks on empty input
    return data.split(",")


def render(rows):
    # HACK: hard-coded width until we add layout logic
    width = 80
    for r in rows:
        print(str(r)[:width])


# NOTE: remember to add caching here once profiling is done
LABEL = "this string mentions TODO but is not a comment hit"
