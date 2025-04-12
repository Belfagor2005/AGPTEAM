#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
"""
#########################################################
#                                                       #
#  AGP - Advanced Graphics BackdropRenderer             #
#  Version: 3.5.0                                       #
#  Created by Lululla (https://github.com/Belfagor2005) #
#  License: CC BY-NC-SA 4.0                             #
#  https://creativecommons.org/licenses/by-nc-sa/4.0    #
#                                                       #
#  Last Modified: "15:14 - 20250401"                    #
#                                                       #
#  Credits:                                             #
#  - Original concept by Lululla                        #
#  - TMDB API integration                               #
#  - TVDB API integration                               #
#  - OMDB API integration                               #
#  - Advanced caching system                            #
#                                                       #
#  Usage of this code without proper attribution        #
#  is strictly prohibited.                              #
#  For modifications and redistribution,                #
#  please maintain this credit header.                  #
#########################################################
"""
__author__ = "Lululla"
__copyright__ = "AGP Team"

import requests
from collections import namedtuple
from random import choices
from requests.adapters import HTTPAdapter

# User Agent Structure with Percentage Distribution
UserAgent = namedtuple('UserAgent', ['ua', 'weight'])

# List updated to March 2025 with real distribution
USER_AGENTS_2025 = [
	UserAgent(ua="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.10 Safari/605.1.1", weight=43.03),
	UserAgent(ua="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.3", weight=21.05),
	UserAgent(ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3", weight=17.34),
	UserAgent(ua="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.3", weight=3.72),
	UserAgent(ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Trailer/93.3.8652.5", weight=2.48),
	UserAgent(ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.", weight=2.48),
	UserAgent(ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.", weight=2.48),
	UserAgent(ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 OPR/117.0.0.", weight=2.48),
	UserAgent(ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.", weight=1.24),
	UserAgent(ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.1958", weight=1.24),
	UserAgent(ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.", weight=1.24),
	UserAgent(ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.3", weight=1.24)
]


class RequestAgent:
	"""Gestione avanzata degli User Agent con distribuzione percentuale"""

	def __init__(self):
		self.agents = USER_AGENTS_2025
		self.weights = [ua.weight for ua in self.agents]
		self.session = None
		self.timeout_connect = 3.05
		self.timeout_read = 10
		self.max_retries = 2
		self.pool_connections = 3,
		self.pool_maxsize = 3

	def get_random_ua(self):
		"""Restituisce un user agent casuale rispettando la distribuzione reale"""
		return choices(
			population=[ua.ua for ua in self.agents],
			weights=self.weights,
			k=1
		)[0]

	def create_session(self, retries=2, backoff_factor=0.5):
		"""Crea una sessione requests configurata"""
		self.session = requests.Session()

		# Configuring adapters with retries
		adapter = HTTPAdapter(
			max_retries=self.max_retries,
			pool_connections=self.pool_connections,
			pool_maxsize=self.pool_maxsize
		)
		self.session.mount('http://', adapter)
		self.session.mount('https://', adapter)

		# Advanced Header
		self.session.headers.update({
			'User-Agent': self.get_random_ua(),
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
			'Accept-Language': 'en-US,en;q=0.9',
			'Accept-Encoding': 'gzip, deflate, br',
			'Connection': 'keep-alive',
			'DNT': '1',
			'Upgrade-Insecure-Requests': '1',
			'Sec-Fetch-Dest': 'document',
			'Sec-Fetch-Mode': 'navigate',
			'Sec-Fetch-Site': 'none',
			'Sec-Fetch-User': '?1'
		})

		return self.session

	def smart_request(self, url, method='GET', **kwargs):
		kwargs.setdefault('timeout', (self.timeout_connect, self.timeout_read))
		if not self.session:
			self.create_session()

		try:
			# print(f"Session active: {self.session is not None}")
			response = self.session.request(method, url, **kwargs)
			# print(f"response = self.session.request: {response}")
			response.raise_for_status()
			# print(f"response: {response}")
			return response
		except requests.exceptions.RequestException as e:
			print(f"Request failed: {str(e)}")
			raise


# Preconfigured Global Instance
request_agent = RequestAgent()


"""
# For single session request
from .Agp_Requests import request_agent

try:
	response = request_agent.smart_request('https://api.example.com/data')
	data = response.json()
except Exception as e:
	logger.error(f"API request failed: {e}")
"""

"""
# personally session
from .Agp_Requests import RequestAgent
custom_agent = RequestAgent()
session = custom_agent.create_session(retries=5)

# Us session for many request
response1 = session.get('https://api.example.com/data1')
response2 = session.get('https://api.example.com/data2')
"""
