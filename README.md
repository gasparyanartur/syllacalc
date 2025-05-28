# Syllacalc

Light script to webscrape Chalmers website to see upcoming reexams.
Populate courses.txt with the desired courses to get a breakdown of upcoming examination dates.

## How to install

1. Install uv: https://docs.astral.sh/uv/getting-started/installation/
2. Setup env:
    > uv sync
3. Update courses.txt with relevant courses
4. Run program:
    > uv run syllacalc.py -y STARTYEAR 