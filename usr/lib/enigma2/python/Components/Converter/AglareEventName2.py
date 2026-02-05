# -*- coding: utf-8 -*-

from Components.Converter.Converter import Converter
from Components.Element import cached
from enigma import eEPGCache, eServiceReference
from time import localtime, time, mktime, strftime
from datetime import datetime
import logging
import gettext
_ = gettext.gettext
# 2025.04.01 @ lululla fix

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


# Define constants for event types
EPG_SOURCE = 'EPG-SAT.DE'
EVENT_REFERENCE = 'IBDCTSERNX'


class AglareEventName2(Converter, object):
	NAME = 0
	NAME_TWEAKED = 1
	SHORT_DESCRIPTION = 2
	EXTENDED_DESCRIPTION = 3
	FULL_DESCRIPTION = 4
	ID = 5
	NEXT_NAME = 6
	NEXT_DESCRIPTION = 7
	NEXT_NAMEWT = 8
	NEXT_NAME_NEXT = 9
	NEXT_NAME_NEXTWT = 10
	NEXT_EVENT_LIST = 11
	NEXT_EVENT_LISTWT = 12
	NEXT_EVENT_LIST2 = 13
	NEXT_EVENT_LISTWT2 = 14
	NEXT_TIME_DURATION = 15
	PRIME_TIME_NO_DURATION = 16
	PRIME_TIME_ONLY_DURATION = 17
	PRIME_TIME_WITH_DURATION = 18
	COMPACT_TIME = 19
	COMPACT_TIMELINE = 20
	AGE_RATING = 21
	NEXT_EVENT_LIST3 = 22

	def __init__(self, type):
		Converter.__init__(self, type)
		self.epgcache = eEPGCache.getInstance()

		# Map input types to internal constants
		event_types = {
			'NameTweaked': self.NAME_TWEAKED,
			'Description': self.SHORT_DESCRIPTION,
			'ExtendedDescription': self.EXTENDED_DESCRIPTION,
			'FullDescription': self.FULL_DESCRIPTION,
			'ID': self.ID,
			'NextName': self.NEXT_NAME,
			'NextNameNext': self.NEXT_NAME_NEXT,
			'NextNameNextWithOutTime': self.NEXT_NAME_NEXTWT,
			'NextNameWithOutTime': self.NEXT_NAMEWT,
			'NextDescription': self.NEXT_DESCRIPTION,
			'NextEventList': self.NEXT_EVENT_LIST,
			'NextEventListWithOutTime': self.NEXT_EVENT_LISTWT,
			'NextEventList2': self.NEXT_EVENT_LIST2,
			'NextEventListWithOutTime2': self.NEXT_EVENT_LISTWT2,
			'NextTimeDuration': self.NEXT_TIME_DURATION,
			'PrimeTimeNoDuration': self.PRIME_TIME_NO_DURATION,
			'PrimeTimeOnlyDuration': self.PRIME_TIME_ONLY_DURATION,
			'PrimeTimeWithDuration': self.PRIME_TIME_WITH_DURATION,
			'CompactTime': self.COMPACT_TIME,
			'CompactTimeline': self.COMPACT_TIMELINE,
			'AgeRating': self.AGE_RATING,
			'NextEventList3': self.NEXT_EVENT_LIST3,
		}
		self.type = event_types.get(type, self.NAME)

	@cached
	def getText(self):
		event = self.source.event
		if not event:
			return ''

		if self.type == self.NAME:
			return event.getEventName()
		elif self.type == self.NAME_TWEAKED:
			return self.getTweakedEventName(event)
		elif self.type == self.SHORT_DESCRIPTION:
			return event.getShortDescription()
		elif self.type == self.EXTENDED_DESCRIPTION:
			return self.getExtendedDescription(event)
		elif self.type == self.FULL_DESCRIPTION:
			return self.getFullDescription(event)
		elif self.type == self.ID:
			return str(event.getEventId())
		elif self.type in [self.PRIME_TIME_NO_DURATION, self.PRIME_TIME_ONLY_DURATION, self.PRIME_TIME_WITH_DURATION]:
			return self.getPrimeTimeDetails()
		elif self.type in [self.NEXT_NAME, self.NEXT_DESCRIPTION, self.NEXT_TIME_DURATION, self.NEXT_NAMEWT]:
			return self.getNextEventDetails()
		elif self.type in [self.NEXT_EVENT_LIST, self.NEXT_EVENT_LISTWT, self.NEXT_EVENT_LIST2, self.NEXT_EVENT_LISTWT2]:
			return self.getNextEventList()
		elif self.type == self.COMPACT_TIME:
			return self.getCompactTimeFormat(event)
		elif self.type == self.COMPACT_TIMELINE:
			return self.getCompactTimeline()
		elif self.type == self.AGE_RATING:
			return self.getAgeRating(event)
		elif self.type in [self.NEXT_EVENT_LIST, self.NEXT_EVENT_LISTWT,
						   self.NEXT_EVENT_LIST2, self.NEXT_EVENT_LISTWT2,
						   self.NEXT_EVENT_LIST3]:
			return self.getNextEventList()
		return ''

	def getTweakedEventName(self, event):
		description = '%s %s' % (event.getEventName().strip(), event.getShortDescription().strip())
		return description.replace('DOLBY, 16:9', '').replace('(', '').replace(')', '').replace('|', '').replace('0+', '').replace('16+', '').replace('6+', '').replace('12+', '').replace('18+', '')

	def getExtendedDescription(self, event):
		text = event.getShortDescription()
		if text and text[-1] not in ['\n', ' ']:
			text += ' '
		return text + event.getExtendedDescription() or event.getEventName()

	def getCompactTimeFormat(self, event):
		start = strftime('%H:%M', localtime(event.getBeginTime()))
		end = strftime('%H:%M', localtime(event.getBeginTime() + event.getDuration()))
		return f"{start}→{end} {event.getEventName()}"

	def getAgeRating(self, event):
		if not event:
			return ''

		# Ensure we have valid methods to call
		if not all(hasattr(event, method) for method in ['getParentalData', 'getEventName',
														 'getShortDescription', 'getExtendedDescription']):
			return ''
		# First try official EPG rating data
		rating = event.getParentalData()
		if rating:
			age = rating.getRating()
			if age > 0:  # 0 means no rating
				# Convert to standard format (+16, +18 etc)
				if age <= 15:  # ETSI standard adds 3 to get actual age
					age += 3
				return f"(+{age})"

		# Fallback to text parsing if no official rating
		name = event.getEventName()
		description = event.getShortDescription() + " " + event.getExtendedDescription()

		# Check both name and description for age indicators
		for text in [name, description]:
			if not text:
				continue

			# Look for common age rating patterns
			if '18+' in text or 'FSK18' in text or '18 rated' in text.lower():
				return '(+18)'
			if '16+' in text or 'FSK16' in text:
				return '(+16)'
			if '12+' in text or 'FSK12' in text:
				return '(+12)'
			if '6+' in text or 'FSK6' in text:
				return '(+6)'
			if '0+' in text or 'FSK0' in text:
				return '(+0)'

		return ''  # Return empty if no rating found

	def getCompactTimeline(self):
		reference = self.source.service
		if not reference:
			return ""

		# Use same lookup method as getNextEventList()
		events = self.epgcache.lookupEvent(['IBDCT', (reference.toString(), 0, -1, -1)])
		if not events:
			return ""

		timeline = []
		now = time()

		for i, event in enumerate(events):
			# Skip first event (current?) if needed
			if i == 0:
				continue

			start = event[1]
			end = start + event[2]
			name = event[4]

			if not name:  # Skip if no event name
				continue

			start_str = strftime('%H:%M', localtime(start))
			end_str = strftime('%H:%M', localtime(end))

			# Current event marker
			prefix = "▶ " if start <= now <= end else ""

			timeline.append(f"{prefix}{start_str}→{end_str} {name}")

			# Limit to 5 events for display
			if len(timeline) >= 10:
				break

		return "\n".join(timeline) if timeline else "No upcoming events"

	def getFullDescription(self, event):
		description = event.getShortDescription()
		extended = event.getExtendedDescription()
		if description and extended:
			description += '\n'
		return description + extended

	def getPrimeTimeDetails(self):
		reference = self.source.service
		current_event = self.source.getCurrentEvent()
		if current_event:
			now = localtime(time())
			dt = datetime(now.tm_year, now.tm_mon, now.tm_mday, 20, 15)
			self.epgcache.startTimeQuery(eServiceReference(reference.toString()), int(mktime(dt.timetuple())))
			next_event = self.epgcache.getNextTimeEntry()
			if next_event and next_event.getBeginTime() <= int(mktime(dt.timetuple())):
				return self.formatPrimeTimeEvent(next_event)
		return ''

	def formatPrimeTimeEvent(self, event):
		begin = strftime('%H:%M', localtime(event.getBeginTime()))
		end = strftime('%H:%M', localtime(event.getBeginTime() + event.getDuration()))
		title = event.getEventName()
		duration = _('%d min') % (event.getDuration() / 60)
		return f"{begin} - {end} ({duration}) {title}"

	def getNextEventDetails(self):
		reference = self.source.service
		info = reference and self.source.info
		if info:
			eventNext = self.epgcache.lookupEvent([EVENT_REFERENCE, (reference.toString(), 1, -1)])
			if eventNext:
				return self.formatNextEvent(eventNext[0])
		return ''

	def formatNextEvent(self, event):
		t = localtime(event[1])
		duration = _('%d min') % (int(0 if event[2] is None else event[2]) / 60)
		if len(event) > 4 and event[4]:
			return f'{t[3]:02d}:{t[4]:02d} ({duration}) {event[4]}'
		return ''

	def getNextEventList(self):
		reference = self.source.service
		info = reference and self.source.info
		if info:
			eventNext = self.epgcache.lookupEvent(['IBDCTSERNX', (reference.toString(), 0, -1, -1)])
			if eventNext:
				listEpg = []
				for i, x in enumerate(eventNext):
					if 0 < i < 10 and x[4]:

						duration = _('%d min') % (int(0 if x[2] is None else x[2]) / 60)
						t = localtime(x[1])

						# Get age rating using proper event object
						ref = eServiceReference(reference.toString())
						event = self.epgcache.lookupEventTime(ref, x[1])
						age_rating = self.getAgeRating(event) if event else ""

						if self.type == self.NEXT_EVENT_LISTWT:
							listEpg.append(f'({duration}) {x[4]}')
						elif self.type == self.NEXT_EVENT_LISTWT2:
							listEpg.append(f'{x[4]} ({duration})')
						elif self.type == self.NEXT_EVENT_LIST2:
							listEpg.append(f'{t[3]:02d}:{t[4]:02d} - {x[4]} ({duration})')
						elif self.type == self.NEXT_EVENT_LIST3:
							listEpg.append(f'{t[3]:02d}:{t[4]:02d} - {x[4]}{" " + age_rating if age_rating else ""} ({duration})')
						else:
							listEpg.append(f'{t[3]:02d}:{t[4]:02d} ({duration}) {x[4]}')
				return '\n'.join(listEpg)
		return ''

	text = property(getText)


"""
# 1. Esempio di Converter per PrimeTimeWithDuration
<screen name="PrimeTimeScreen" position="center,center" size="1280,720" title="Prime Time Events">
	<widget name="primeTimeEvent" source="ServiceEvent" render="Label" position="50,50" size="1180,50" font="Bold; 26" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="gold" valign="center">
		<convert type="AglareEventName2">PrimeTimeWithDuration</convert>
	</widget>
</screen>
# 2. Esempio di Converter per NextEventList

<screen name="NextEventListScreen" position="center,center" size="1280,720" title="Next Events">
	<widget name="nextEventList" source="ServiceEvent" render="Label" position="50,50" size="1180,50" font="Bold; 24" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="silver" valign="center">
		<convert type="AglareEventName2">NextEventList</convert>
	</widget>
</screen>
# 3. Esempio di Converter per NextEventList2

<screen name="NextEventList2Screen" position="center,center" size="1280,720" title="Next Events 2">
	<widget name="nextEventList2" source="ServiceEvent" render="Label" position="50,50" size="1180,50" font="Bold; 24" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="blue" valign="center">
		<convert type="AglareEventName2">NextEventList2</convert>
	</widget>
</screen>
# 4. Esempio di Converter per NextTimeDuration

<screen name="NextTimeDurationScreen" position="center,center" size="1280,720" title="Next Event Time Duration">
	<widget name="nextTimeDuration" source="ServiceEvent" render="Label" position="50,50" size="1180,50" font="Bold; 24" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="green" valign="center">
		<convert type="AglareEventName2">NextTimeDuration</convert>
	</widget>
</screen>
# 5. Esempio di Converter per PrimeTimeNoDuration

<screen name="PrimeTimeNoDurationScreen" position="center,center" size="1280,720" title="Prime Time No Duration">
	<widget name="primeTimeNoDuration" source="ServiceEvent" render="Label" position="50,50" size="1180,50" font="Bold; 26" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="red" valign="center">
		<convert type="AglareEventName2">PrimeTimeNoDuration</convert>
	</widget>
</screen>
# 6. Esempio di Converter per NextNameNext

<screen name="NextNameNextScreen" position="center,center" size="1280,720" title="Next Name Next">
	<widget name="nextNameNext" source="ServiceEvent" render="Label" position="50,50" size="1180,50" font="Bold; 24" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="purple" valign="center">
		<convert type="AglareEventName2">NextNameNext</convert>
	</widget>
</screen>
# 7. Esempio di Converter per FullDescription

<screen name="FullDescriptionScreen" position="center,center" size="1280,720" title="Full Event Description">
	<widget name="fullDescription" source="ServiceEvent" render="Label" position="50,50" size="1180,50" font="Bold; 24" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="orange" valign="center">
		<convert type="AglareEventName2">FullDescription</convert>
	</widget>
</screen>
# 8. Esempio di Converter per NextNameWithOutTime

<screen name="NextNameWithoutTimeScreen" position="center,center" size="1280,720" title="Next Name Without Time">
	<widget name="nextNameWithoutTime" source="ServiceEvent" render="Label" position="50,50" size="1180,50" font="Bold; 24" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="yellow" valign="center">
		<convert type="AglareEventName2">NextNameWithOutTime</convert>
	</widget>
</screen>
# 9. Esempio di Converter per ID

<screen name="EventIDScreen" position="center,center" size="1280,720" title="Event ID">
	<widget name="eventID" source="ServiceEvent" render="Label" position="50,50" size="1180,50" font="Bold; 24" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="cyan" valign="center">
		<convert type="AglareEventName2">ID</convert>
	</widget>
</screen>
# 10. Esempio di Converter per NextDescription

<screen name="NextDescriptionScreen" position="center,center" size="1280,720" title="Next Event Description">
	<widget name="nextDescription" source="ServiceEvent" render="Label" position="50,50" size="1180,50" font="Bold; 24" backgroundColor="background" transparent="1" noWrap="1" zPosition="1" foregroundColor="magenta" valign="center">
		<convert type="AglareEventName2">NextDescription</convert>
	</widget>
</screen>
"""
