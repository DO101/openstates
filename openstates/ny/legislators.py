#!/usr/bin/env python
import re

from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class NYLegislatorScraper(LegislatorScraper):
    state = 'ny'

    def scrape(self, chamber, term):
        if chamber == 'upper':
            self.scrape_upper(term)
        else:
            self.scrape_lower(term)

    def scrape_upper(self, term):
        url = "http://www.nysenate.gov/senators"
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link in page.xpath('//a[contains(@href, "/senator/")]'):
                if link.text in (None, 'Contact', 'RSS'):
                    continue
                name = link.text.strip()

                district = link.xpath("string(../../../div[3]/span[1])")
                district = re.match(r"District (\d+)", district).group(1)

                photo_link = link.xpath("../../../div[1]/span/a/img")[0]
                photo_url = photo_link.attrib['src']

                legislator = Legislator(term, 'upper', district,
                                        name, party="Unknown",
                                        photo_url=photo_url)
                legislator.add_source(url)

                contact_link = link.xpath("../span[@class = 'contact']/a")[0]
                contact_url = contact_link.attrib['href']
                self.scrape_upper_contact_info(legislator, contact_url)

                legislator['url'] = contact_url.replace('/contact', '')

                self.save_legislator(legislator)

    def scrape_upper_contact_info(self, legislator, url):
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            legislator.add_source(url)

            email = page.xpath('//span[@class="spamspan"]')[0].text_content()
            email = email.replace(' [at] ', '@').replace(' [dot] ', '.')
            if email:
                legislator['email'] = email

            dist_str = page.xpath("string(//div[@class = 'district'])")
            match = re.findall(r'\(([A-Za-z,\s]+)\)', dist_str)
            if match:
                match = match[0].split(', ')
                party_map = {'D': 'Democratic', 'R': 'Republican',
                             'WF': 'Working Families',
                             'C': 'Conservative',
                             'IP': 'Independence',
                            }
                parties = [party_map.get(p.strip(), p.strip()) for p in match
                           if p.strip()]
                if 'Republican' in parties:
                    party = 'Republican'
                    parties.remove('Republican')
                elif 'Democratic' in parties:
                    party = 'Democratic'
                    parties.remove('Democratic')
                legislator['roles'][0]['party'] = party
                legislator['roles'][0]['other_parties'] = parties

            try:
                span = page.xpath("//span[. = 'Albany Office']/..")[0]
                address = span.xpath("string(div[1])").strip()
                address += "\nAlbany, NY 12247"

                phone = span.xpath("div[@class='tel']/span[@class='value']")[0]
                phone = phone.text.strip()

                office = dict(
                        name='Capitol Office',
                        type='capitol', phone=phone,
                        fax=None, email=None,
                        address=address)

                legislator.add_office(**office)

            except IndexError:
                # Sometimes contact pages are just plain broken
                pass

            try:
                span = page.xpath("//span[. = 'District Office']/..")[0]
                address = span.xpath("string(div[1])").strip() + "\n"
                address += span.xpath(
                    "string(span[@class='locality'])").strip() + ", "
                address += span.xpath(
                    "string(span[@class='region'])").strip() + " "
                address += span.xpath(
                    "string(span[@class='postal-code'])").strip()

                phone = span.xpath("div[@class='tel']/span[@class='value']")[0]
                phone = phone.text.strip()

                office = dict(
                        name='District Office',
                        type='district', phone=phone,
                        fax=None, email=None,
                        address=address)

                legislator.add_office(**office)
            except IndexError:
                # No district office yet?
                pass

    def scrape_lower(self, term):
        url = "http://assembly.state.ny.us/mem/?sh=email"
        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            for link, email in zip(page.xpath("//a[contains(@href, '/mem/')]"),
                                   page.xpath("//a[contains(@href, 'mailto')]")):

                name = link.text.strip()
                if name == 'Assembly Members':
                    continue

                # empty seats
                if 'Assembly District' in name:
                    continue

                district = link.xpath("string(../following-sibling::"
                                      "div[@class = 'email2'][1])")
                district = district.rstrip('rthnds')

                leg_url = link.get('href')
                legislator = Legislator(term, 'lower', district,
                                        name, party="Unknown",
                                        url=leg_url)
                legislator.add_source(url)

                # Legislator
                self.scrape_lower_offices(leg_url, legislator)

                email = email.text_content().strip()
                if email:
                    legislator['email'] = email
                self.save_legislator(legislator)

    def scrape_lower_offices(self, url, legislator):
        html = self.urlopen(url)
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        contact = doc.xpath('//div[@id="addrinfo"]')[0]
        col = 1
        while True:
            address_data = contact.xpath('div[@class="addrcol%d"]' % col)
            col += 1
            if not address_data:
                break
            for data in address_data:
                data = (data.xpath('div[@class="officehdg"]/text()'),
                        data.xpath('div[@class="officeaddr"]/text()'))
                ((office_name,), address) = data
                if 'district' in office_name:
                    office_type = 'district'
                else:
                    office_type = 'capitol'

                phone = address.pop().strip()
                office = dict(
                    name=office_name, type=office_type, phone=phone,
                    fax=None, email=None,
                    address=''.join(address))

                legislator.add_office(**office)
