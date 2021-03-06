from billy.scrape.committees import CommitteeScraper, Committee
import lxml.html

_COMMITTEE_URL = 'http://legislature.idaho.gov/%s/committees.cfm' # house/senate
_JOINT_URL = 'http://legislature.idaho.gov/about/jointcommittees.htm'

_CHAMBERS = {'upper':'senate', 'lower':'house'}
_REV_CHAMBERS = {'senate':'upper', 'house':'lower'}
_TD_ONE = ('committee', 'description', 'office_hours', 'secretary', 'office_phone')
_TD_TWO = ('committee', 'office_hours', 'secretary', 'office_phone')

def clean_name(name):
    return name.replace(u'\xa0', ' ')
    
class IDCommitteeScraper(CommitteeScraper):
    """Currently only committees from the latest regular session are
    available through html. Membership for prior terms are available via the
    committee minutes .pdf files at
    http://legislature.idaho.gov/sessioninfo/2009/standingcommittees/committeeminutesindex.htm
    and the pdfs I have encountered from Idaho convert to html
    consistantly, so we could get membership and committee minutes if we really
    want."""
    jurisdiction = 'id'

    def get_jfac(self, name, url):
        """gets membership info for the Joint Finance and Appropriations
        Committee."""
        with self.urlopen(url) as jfac_page:
            html = lxml.html.fromstring(jfac_page)
            table = html.xpath('body/table/tr/td[2]/table')[0]
            committee = Committee('joint', name)
            for row in table.xpath('tr')[1:]:
                senate, house = row.xpath('td/strong')
                senate = senate.text.replace(u'\xa0', ' ')
                house = house.text.replace(u'\xa0', ' ')
                if ',' in senate:
                    committee.add_member(*senate.split(','), chamber='upper')
                else:
                    committee.add_member(senate, chamber='upper')
                if ',' in house:
                    committee.add_member(*house.split(','), chamber='lower')
                else:
                    committee.add_member(house, chamber='lower')

            committee.add_source(url)
            self.save_committee(committee)

    def get_jlfc(self, name, url):
        """Gets info for the Joint Legislative Oversight Committee"""
        with self.urlopen(url) as jlfc_page:
            html = lxml.html.fromstring(jlfc_page)
            committee = Committee('joint', name)
            member_path = '//h3[contains(text(), "%s")]/following-sibling::p[1]'
            for chamber in ('Senate', 'House'):
                members = html.xpath(member_path % chamber)[0]\
                              .text_content().split('\r\n')
                for member in members:
                    if member.strip():
                        committee.add_member(*member.replace(u'\xa0', ' ').split(','),
                                         chamber=_REV_CHAMBERS[chamber.lower()])
            committee.add_source(url)
            self.save_committee(committee)

    def get_jmfc(self, name, url):
        """Gets the Joint Millennium Fund Committee info"""
        with self.urlopen(url) as jfmc_page:
            html = lxml.html.fromstring(jfmc_page)
            committee = Committee('joint', name)
            table = html.xpath('//table')[2]
            for row in table.xpath('tbody/tr'):
                senate, house = [ td.text.replace('\r\n', ' ').replace(u'\xa0', ' ') \
                                  for td in row.xpath('td') ]
                committee.add_member( *senate.strip('Sen.').strip().split(',') )
                committee.add_member( *house.strip('Rep.').strip().split(',') )
            committee.add_source(url)
            self.save_committee(committee)

    def scrape_committees(self, chamber):
        url = _COMMITTEE_URL % _CHAMBERS[chamber]
        with self.urlopen(url) as page:
            html = lxml.html.fromstring(page)
            table = html.xpath('body/table/tr/td[2]/table')[0]

            for row in table.xpath('tr')[1:]:
                # committee name, description, hours of operation,
                # secretary and office_phone
                text = list(row[0].itertext())
                if len(text) > 4:
                    com = dict(zip(_TD_ONE, text))
                else:
                    com = dict(zip(_TD_TWO, text))
                committee = Committee(chamber, **com)
                committee.add_source(url)

                # membership
                for td in row[1:]:
                    for elem in td:
                        position, leg = elem.text, elem.tail
                        if position and leg:
                            committee.add_member(leg.replace(u'\xa0', ' '), role=position)
                        elif leg:
                            committee.add_member(leg.replace(u'\xa0', ' '))
                self.save_committee(committee)

    def scrape_joint_committees(self):
        url = 'http://legislature.idaho.gov/about/jointcommittees.htm'
        with self.urlopen(url) as page:
            html = lxml.html.fromstring(page)
            html.make_links_absolute(url)
            joint_li = html.xpath('//td[contains(h1, "Joint")]/ul/li')
            for li in joint_li:
                name, url = li[0].text, li[0].get('href')
                if 'Joint Finance-Appropriations Committee' in name:
                    self.get_jfac(name, url)
                elif 'Joint Legislative Oversight Committee' in name:
                    self.get_jlfc(name, url)
                elif name == 'Joint Millennium Fund Committee':
                    self.get_jmfc(name, url)
                elif name == 'Economic Outlook and Revenue Assessment Committee':
                    committee = Committee('joint', name)
                    committee.add_source(url)
                    # no membership available
                    #self.save_committee(committee)
                else:
                    self.log('Unknown committee: %s %s' % (name, url))


    def scrape(self, chamber, term):
        """
        Scrapes Idaho committees for the latest term.
        """
        self.validate_term(term, latest_only=True)

        self.scrape_committees(chamber)
        self.scrape_joint_committees()
