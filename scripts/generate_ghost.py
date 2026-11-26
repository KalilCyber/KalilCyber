"""Generate an animated GitHub contribution calendar (SVG, standard library only)."""
import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date weekday contributionCount } }
      }
    }
  }
}
"""


def fetch_calendar(login, token):
    if not token:
        raise RuntimeError("GITHUB_TOKEN is missing")
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json", "User-Agent": "Ghost-Protocol"},
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors") or not result.get("data", {}).get("user"):
        raise RuntimeError(f"GitHub GraphQL query failed: {result.get('errors', 'user unavailable')}")
    return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def demo_calendar():
    """Synthetic fixture for local testing only; never used by the workflow."""
    start = date(2025, 11, 30)
    weeks = []
    for col in range(52):
        days = []
        for row in range(7):
            n = (col * 11 + row * 7 + col * row * 3) % 19
            count = n % 8 + 1 if n > 9 else 0
            days.append({"date": str(start + timedelta(days=col * 7 + row)),
                         "weekday": row, "contributionCount": count})
        weeks.append({"contributionDays": days})
    return {"weeks": weeks, "totalContributions": sum(d["contributionCount"]
            for w in weeks for d in w["contributionDays"])}


def render(calendar, login, demo=False):
    weeks = calendar["weeks"]
    if not weeks or len(weeks) > 54:
        raise ValueError("Unexpected contribution calendar size")
    width, height, pitch, cell = 1160, 320, 20, 15
    left = (width - ((len(weeks) - 1) * pitch + cell)) // 2
    top = 94
    span = (len(weeks) - 1) * pitch + cell
    total = calendar["totalContributions"]
    active = sum(d["contributionCount"] > 0 for w in weeks for d in w["contributionDays"])
    maximum = max((d["contributionCount"] for w in weeks for d in w["contributionDays"]), default=0)
    colors = ["#0c1c13", "#104b29", "#148447", "#17c75b", "#63ff9b"]
    p = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
<title>Ghost Protocol — {escape(login)} contribution network</title>
<desc>Animated scan of a GitHub contribution calendar. {'Synthetic demo data.' if demo else 'Counts returned by GitHub.'} {total} contributions, {active} active days.</desc>
<defs>
  <linearGradient id="bg" x2="0" y2="1"><stop stop-color="#081b11"/><stop offset="1" stop-color="#030906"/></linearGradient>
  <pattern id="lines" width="5" height="5" patternUnits="userSpaceOnUse"><path d="M0 0H5" stroke="#45ff7a" stroke-opacity=".035"/></pattern>
  <linearGradient id="beam"><stop stop-color="#00ff41" stop-opacity="0"/><stop offset="1" stop-color="#00ff41" stop-opacity=".32"/></linearGradient>
  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<rect width="1160" height="320" rx="8" fill="url(#bg)"/>
<rect width="1160" height="320" rx="8" fill="url(#lines)"/>
<path d="M16 48V16H48 M1112 16H1144V48 M16 272V304H48 M1112 304H1144V272" fill="none" stroke="#00ff41" stroke-width="2"/>
<g font-family="monospace">
<text x="580" y="40" text-anchor="middle" font-weight="bold" font-size="27" letter-spacing="6" fill="#9affb8">GHOST PROTOCOL</text>
<text x="580" y="64" text-anchor="middle" font-size="13" letter-spacing="2" fill="#44c979">CYBERNETIC CONTRIBUTION NETWORK {'// DEMO' if demo else '// ' + escape(login.upper())}</text>
<path d="M28 76H1132 M28 244H1132" stroke="#164f30"/>
''']
    for col, week in enumerate(weeks):
        x = left + col * pitch
        if col % 7 == 0:
            p.append(f'<text x="{x}" y="87" fill="#4d956a" font-size="9">{col:02X}</text>')
        # The scanner reaches this column at this fraction of the full loop.
        t = 0.04 + 0.80 * (col / max(1, len(weeks) - 1))
        for day in week["contributionDays"]:
            row, count = day["weekday"], day["contributionCount"]
            if not 0 <= row <= 6 or count < 0:
                raise ValueError("Invalid calendar day")
            y = top + row * pitch
            level = 0 if count == 0 else min(4, 1 + (count - 1) * 4 // max(1, maximum))
            color = colors[level]
            p.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{color}" fill-opacity=".55" stroke="#16442a" stroke-width=".5"><title>{escape(day["date"])}: {count} contributions</title></rect>')
            if count:
                p.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{color}" opacity="0"><animate attributeName="opacity" values="0;0;1;1" keyTimes="0;{t:.5f};{t+.025:.5f};1" dur="18s" repeatCount="indefinite"/></rect>')
    # Sweep from the first week to the last, then pause with the scan complete.
    p.append(f'''<g transform="translate({left} 0)">
<g><animateTransform attributeName="transform" type="translate" values="0 0;0 0;{span-cell} 0;{span-cell} 0" keyTimes="0;.04;.84;1" dur="18s" repeatCount="indefinite"/>
<rect x="-36" y="91" width="44" height="141" fill="url(#beam)"/>
<path d="M7.5 91V232" stroke="#a8ffc0" stroke-width="1.7" filter="url(#glow)"/>
<path d="M1 91L7.5 85L14 91Z" fill="#baffcd"/>
<circle cx="7.5" cy="234" r="3" fill="#baffcd"/>
</g></g>
<text x="35" y="266" fill="#00ff41" font-size="13">[+] DECODING CONTRIBUTION DATA<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.87;.88;1" dur="18s" repeatCount="indefinite"/></text>
<text x="35" y="266" fill="#a8ffc0" font-size="13" opacity="0">[+] SCAN COMPLETE<animate attributeName="opacity" values="0;0;1;1" keyTimes="0;.87;.88;1" dur="18s" repeatCount="indefinite"/></text>
<text x="1125" y="266" text-anchor="end" fill="#8addaa" font-size="13">CONTRIBUTIONS: {total}  |  ACTIVE DAYS: {active}</text>
<rect x="35" y="280" width="1090" height="4" rx="2" fill="#103b23"/>
<rect x="35" y="280" width="0" height="4" rx="2" fill="#00ff41"><animate attributeName="width" values="0;0;1090;1090" keyTimes="0;.04;.84;1" dur="18s" repeatCount="indefinite"/></rect>
<text x="35" y="299" font-size="10" fill="#4d956a">GHOST_AGENT_01 // VISUALIZATION ONLY</text>
<text x="1125" y="299" text-anchor="end" font-size="10" fill="#4d956a">{'SYNTHETIC TEST' if demo else 'SOURCE: GITHUB GRAPHQL API'}</text>
</g></svg>''')
    return '\n'.join(p)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user', default='KalilCyber')
    parser.add_argument('--output', type=Path, default=Path('assets/ghost-protocol.svg'))
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    calendar = demo_calendar() if args.demo else fetch_calendar(args.user, os.getenv('GITHUB_TOKEN'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(calendar, args.user, args.demo), encoding='utf-8')
    print(f'Generated {args.output}')


if __name__ == '__main__':
    main()
