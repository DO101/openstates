import lxml.html


metadata = dict(
    name='Delaware',
    abbreviation='de',
    capitol_timezone='America/New_York',
    legislature_name='Delaware General Assembly',
    chambers={
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'sessions': ['146'],
         'start_year': 2011, 'end_year': 2012},

        {'name': '2013-2014',
         'sessions': ['147'],
         'start_year': 2013, 'end_year': 2014},
    ],
    session_details={
        '146': {'display_name': '146th General Assembly',
                '_scraped_name': 'GA 146',
               },
        '147': {'display_name': '147th General Assembly',
                '_scraped_name': 'GA 147',
               },
    },
    feature_flags=['events', 'influenceexplorer'],
    _ignored_scraped_sessions=['GA 145', 'GA 144', 'GA 143', 'GA 142',
                               'GA 141', 'GA 140', 'GA 139', 'GA 138']
)


def session_list():
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://legis.delaware.gov/',
        "//select[@name='gSession']/option/text()")
    sessions = [session.strip() for session in sessions]
    sessions.remove("Session")
    return sessions


def extract_text(doc, data):
    if doc['mimetype'] == 'text/html':
        doc = lxml.html.fromstring(data)
        return ' '.join(x.text_content()
                        for x in doc.xpath('//p[@class="MsoNormal"]'))
