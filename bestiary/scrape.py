import json

from bs4 import BeautifulSoup

def parse_bestiary():
    with open('bestiary.html', 'r') as f:
        soup = BeautifulSoup(f.read())

    results = []
    for entry in soup.find_all('div'):
        results.append({
            'href': entry.select_one('a')['href'],
            'name': entry.select_one('.ecgen__name').text,
            'species': entry.select_one('.col-4-1').text,
            'cr': entry.select_one('.col-1-7').text,
            'source': entry.select_one('.col-2').text
        })

    with open('out.json', 'w') as f:
        json.dump(results, f, indent=4)


