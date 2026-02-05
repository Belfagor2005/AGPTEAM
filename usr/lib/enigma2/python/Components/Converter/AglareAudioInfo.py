# -*- coding: utf-8 -*-

from enigma import iPlayableService
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll
import logging
import gettext
_ = gettext.gettext

# 2025.04.01 @ lululla fix


class AglareAudioInfo(Poll, Converter):
    """Enhanced audio information converter with codec detection and language support"""

    GET_AUDIO_ICON = 0
    GET_AUDIO_CODEC = 1

    def __init__(self, type):
        Converter.__init__(self, type)
        Poll.__init__(self)
        self.logger = logging.getLogger("AglareAudioInfo")

        # Configuration
        self.poll_interval = 1000  # ms
        self.poll_enabled = True

        # Language settings
        self.full_language_names = {
            # ISO 639-1 codes
            'aa': 'Afar', 'ab': 'Abkhazian', 'af': 'Afrikaans', 'ak': 'Akan',
            'am': 'Amharic', 'ar': 'Arabic', 'as': 'Assamese', 'ay': 'Aymara',
            'az': 'Azerbaijani', 'ba': 'Bashkir', 'be': 'Belarusian', 'bg': 'Bulgarian',
            'bh': 'Bihari', 'bi': 'Bislama', 'bn': 'Bengali', 'bo': 'Tibetan',
            'br': 'Breton', 'ca': 'Catalan', 'co': 'Corsican', 'cs': 'Czech',
            'cy': 'Welsh', 'da': 'Danish', 'de': 'German', 'dz': 'Dzongkha',
            'el': 'Greek', 'en': 'English', 'eo': 'Esperanto', 'es': 'Spanish',
            'et': 'Estonian', 'eu': 'Basque', 'fa': 'Persian', 'fi': 'Finnish',
            'fj': 'Fijian', 'fo': 'Faroese', 'fr': 'French', 'fy': 'Frisian',
            'ga': 'Irish', 'gd': 'Scottish Gaelic', 'gl': 'Galician', 'gn': 'Guarani',
            'gu': 'Gujarati', 'ha': 'Hausa', 'he': 'Hebrew', 'hi': 'Hindi',
            'hr': 'Croatian', 'hu': 'Hungarian', 'hy': 'Armenian', 'ia': 'Interlingua',
            'id': 'Indonesian', 'ie': 'Interlingue', 'ik': 'Inupiaq', 'is': 'Icelandic',
            'it': 'Italian', 'iu': 'Inuktitut', 'ja': 'Japanese', 'jw': 'Javanese',
            'ka': 'Georgian', 'kk': 'Kazakh', 'kl': 'Kalaallisut', 'km': 'Khmer',
            'kn': 'Kannada', 'ko': 'Korean', 'ks': 'Kashmiri', 'ku': 'Kurdish',
            'ky': 'Kirghiz', 'la': 'Latin', 'lb': 'Luxembourgish', 'ln': 'Lingala',
            'lo': 'Lao', 'lt': 'Lithuanian', 'lv': 'Latvian', 'mg': 'Malagasy',
            'mi': 'Maori', 'mk': 'Macedonian', 'ml': 'Malayalam', 'mn': 'Mongolian',
            'mo': 'Moldavian', 'mr': 'Marathi', 'ms': 'Malay', 'mt': 'Maltese',
            'my': 'Burmese', 'na': 'Nauru', 'ne': 'Nepali', 'nl': 'Dutch',
            'no': 'Norwegian', 'oc': 'Occitan', 'om': 'Oromo', 'or': 'Oriya',
            'pa': 'Punjabi', 'pl': 'Polish', 'ps': 'Pashto', 'pt': 'Portuguese',
            'qu': 'Quechua', 'rm': 'Romansh', 'rn': 'Kirundi', 'ro': 'Romanian',
            'ru': 'Russian', 'rw': 'Kinyarwanda', 'sa': 'Sanskrit', 'sd': 'Sindhi',
            'sg': 'Sangro', 'sh': 'Serbo-Croatian', 'si': 'Sinhalese', 'sk': 'Slovak',
            'sl': 'Slovenian', 'sm': 'Samoan', 'sn': 'Shona', 'so': 'Somali',
            'sq': 'Albanian', 'sr': 'Serbian', 'ss': 'Siswati', 'st': 'Sesotho',
            'su': 'Sundanese', 'sv': 'Swedish', 'sw': 'Swahili', 'ta': 'Tamil',
            'te': 'Telugu', 'tg': 'Tajik', 'th': 'Thai', 'ti': 'Tigrinya',
            'tk': 'Turkmen', 'tl': 'Tagalog', 'tn': 'Setswana', 'to': 'Tonga',
            'tr': 'Turkish', 'ts': 'Tsonga', 'tt': 'Tatar', 'tw': 'Twi',
            'ug': 'Uighur', 'uk': 'Ukrainian', 'ur': 'Urdu', 'uz': 'Uzbek',
            'vi': 'Vietnamese', 'vo': 'Volapük', 'wo': 'Wolof', 'xh': 'Xhosa',
            'yi': 'Yiddish', 'yo': 'Yoruba', 'za': 'Zhuang', 'zh': 'Chinese',
            'zu': 'Zulu',

            # Common 3-letter abbreviations
            'aar': 'Afar', 'abk': 'Abkhazian', 'afr': 'Afrikaans', 'aka': 'Akan',
            'alb': 'Albanian', 'amh': 'Amharic', 'ara': 'Arabic', 'arg': 'Aragonese',
            'arm': 'Armenian', 'asm': 'Assamese', 'ava': 'Avaric', 'ave': 'Avestan',
            'aym': 'Aymara', 'aze': 'Azerbaijani', 'bak': 'Bashkir', 'bam': 'Bambara',
            'baq': 'Basque', 'bel': 'Belarusian', 'ben': 'Bengali', 'bih': 'Bihari',
            'bis': 'Bislama', 'bos': 'Bosnian', 'bre': 'Breton', 'bul': 'Bulgarian',
            'bur': 'Burmese', 'cat': 'Catalan', 'cha': 'Chamorro', 'che': 'Chechen',
            'chi': 'Chinese', 'chu': 'Church Slavic', 'chv': 'Chuvash', 'cor': 'Cornish',
            'cos': 'Corsican', 'cre': 'Cree', 'cze': 'Czech', 'dan': 'Danish',
            'div': 'Divehi', 'dut': 'Dutch', 'dzo': 'Dzongkha', 'eng': 'English',
            'epo': 'Esperanto', 'est': 'Estonian', 'ewe': 'Ewe', 'fao': 'Faroese',
            'fij': 'Fijian', 'fin': 'Finnish', 'fre': 'French', 'fry': 'Frisian',
            'ful': 'Fulah', 'geo': 'Georgian', 'ger': 'German', 'gla': 'Gaelic',
            'gle': 'Irish', 'glg': 'Galician', 'glv': 'Manx', 'gre': 'Greek',
            'grn': 'Guarani', 'guj': 'Gujarati', 'hat': 'Haitian', 'hau': 'Hausa',
            'heb': 'Hebrew', 'her': 'Herero', 'hin': 'Hindi', 'hmo': 'Hiri Motu',
            'hrv': 'Croatian', 'hun': 'Hungarian', 'ibo': 'Igbo', 'ice': 'Icelandic',
            'ido': 'Ido', 'iii': 'Sichuan Yi', 'iku': 'Inuktitut', 'ile': 'Interlingue',
            'ina': 'Interlingua', 'ind': 'Indonesian', 'ipk': 'Inupiaq', 'ita': 'Italian',
            'jav': 'Javanese', 'jpn': 'Japanese', 'kal': 'Kalaallisut', 'kan': 'Kannada',
            'kas': 'Kashmiri', 'kau': 'Kanuri', 'kaz': 'Kazakh', 'khm': 'Khmer',
            'kik': 'Kikuyu', 'kin': 'Kinyarwanda', 'kir': 'Kirghiz', 'kom': 'Komi',
            'kon': 'Kongo', 'kor': 'Korean', 'kua': 'Kuanyama', 'kur': 'Kurdish',
            'lao': 'Lao', 'lat': 'Latin', 'lav': 'Latvian', 'lim': 'Limburgish',
            'lin': 'Lingala', 'lit': 'Lithuanian', 'ltz': 'Luxembourgish', 'lub': 'Luba-Katanga',
            'lug': 'Ganda', 'mac': 'Macedonian', 'mah': 'Marshallese', 'mal': 'Malayalam',
            'mao': 'Maori', 'mar': 'Marathi', 'may': 'Malay', 'mlg': 'Malagasy',
            'mlt': 'Maltese', 'mon': 'Mongolian', 'nau': 'Nauru', 'nav': 'Navajo',
            'nbl': 'Ndebele', 'nde': 'Ndebele', 'ndo': 'Ndonga', 'nep': 'Nepali',
            'nno': 'Norwegian Nynorsk', 'nob': 'Norwegian Bokmål', 'nor': 'Norwegian',
            'nya': 'Chichewa', 'oci': 'Occitan', 'oji': 'Ojibwa', 'ori': 'Oriya',
            'orm': 'Oromo', 'oss': 'Ossetian', 'pan': 'Panjabi', 'per': 'Persian',
            'pli': 'Pali', 'pol': 'Polish', 'por': 'Portuguese', 'pus': 'Pushto',
            'que': 'Quechua', 'roh': 'Romansh', 'rum': 'Romanian', 'run': 'Rundi',
            'rus': 'Russian', 'sag': 'Sango', 'san': 'Sanskrit', 'sin': 'Sinhalese',
            'slo': 'Slovak', 'slv': 'Slovenian', 'sme': 'Northern Sami', 'smo': 'Samoan',
            'sna': 'Shona', 'snd': 'Sindhi', 'som': 'Somali', 'sot': 'Sotho',
            'spa': 'Spanish', 'srd': 'Sardinian', 'srp': 'Serbian', 'ssw': 'Swati',
            'sun': 'Sundanese', 'swa': 'Swahili', 'swe': 'Swedish', 'tah': 'Tahitian',
            'tam': 'Tamil', 'tat': 'Tatar', 'tel': 'Telugu', 'tgk': 'Tajik',
            'tgl': 'Tagalog', 'tha': 'Thai', 'tib': 'Tibetan', 'tir': 'Tigrinya',
            'ton': 'Tonga', 'tsn': 'Tswana', 'tso': 'Tsonga', 'tuk': 'Turkmen',
            'tur': 'Turkish', 'twi': 'Twi', 'uig': 'Uighur', 'ukr': 'Ukrainian',
            'urd': 'Urdu', 'uzb': 'Uzbek', 'ven': 'Venda', 'vie': 'Vietnamese',
            'vol': 'Volapük', 'wel': 'Welsh', 'wln': 'Walloon', 'wol': 'Wolof',
            'xho': 'Xhosa', 'yid': 'Yiddish', 'yor': 'Yoruba', 'zha': 'Zhuang',
            'zul': 'Zulu',

            # Common broadcast language codes
            'afr': 'Afrikaans', 'tsn': 'Tswana', 'sot': 'Sotho', 'tso': 'Tsonga',
            'ara': 'Arabic', 'fas': 'Persian', 'pus': 'Pashto', 'kur': 'Kurdish',
            'aze': 'Azerbaijani', 'geo': 'Georgian', 'arm': 'Armenian', 'abk': 'Abkhaz',
            'bel': 'Belarusian', 'pol': 'Polish', 'por': 'Portuguese', 'ita': 'Italian',
            'chu': 'Church Slavic', 'crp': 'Creoles and pidgins', 'cpp': 'Creoles and pidgins',
            'cjy': 'Jinyu', 'mnp': 'Min Bei', 'cpx': 'Pu-Xian', 'czo': 'Min Zhong',
            'cjy': 'Jinyu', 'wxa': 'Waxianghua', 'czh': 'Huizhou', 'cdo': 'Min Dong',
            'cmn': 'Mandarin', 'yue': 'Cantonese', 'wuu': 'Wu', 'hsn': 'Xiang',
            'cnp': 'Northern Pinghua', 'cjy': 'Jinyu', 'wxa': 'Waxianghua',
            'cpe': 'Creoles and pidgins', 'cpf': 'Creoles and pidgins', 'crs': 'Seselwa',
            'csp': 'Southern Pinghua', 'cnp': 'Northern Pinghua', 'cjy': 'Jinyu',
            'cym': 'Welsh', 'lat': 'Latin', 'srd': 'Sardinian', 'scn': 'Sicilian',
            'czh': 'Huizhou', 'cjy': 'Jinyu', 'mnp': 'Min Bei', 'cpx': 'Pu-Xian',
            'czo': 'Min Zhong', 'csp': 'Southern Pinghua', 'cnp': 'Northern Pinghua',
            'dan': 'Danish', 'isl': 'Icelandic', 'nor': 'Norwegian', 'sme': 'Sami',
            'est': 'Estonian', 'lav': 'Latvian', 'lit': 'Lithuanian', 'ron': 'Romanian',
            'fra': 'French', 'deu': 'German', 'ell': 'Greek', 'ces': 'Czech',
            'fry': 'Western Frisian', 'gla': 'Scottish Gaelic', 'gle': 'Irish',
            'glv': 'Manx', 'cor': 'Cornish', 'bre': 'Breton', 'cos': 'Corsican',
            'hak': 'Hakka', 'nan': 'Min Nan', 'cdo': 'Min Dong', 'gan': 'Gan',
            'hau': 'Hausa', 'yor': 'Yoruba', 'ibo': 'Igbo', 'kin': 'Kinyarwanda',
            'haw': 'Hawaiian', 'mao': 'Maori', 'smo': 'Samoan', 'mlt': 'Maltese',
            'hun': 'Hungarian', 'slk': 'Slovak', 'slv': 'Slovenian', 'hrv': 'Croatian',
            'kab': 'Kabyle', 'mlg': 'Malagasy', 'div': 'Dhivehi', 'nep': 'Nepali',
            'kir': 'Kyrgyz', 'tuk': 'Turkmen', 'uig': 'Uyghur', 'uzb': 'Uzbek',
            'krc': 'Karachay-Balkar', 'kum': 'Kumyk', 'lez': 'Lezgian', 'nog': 'Nogai',
            'lld': 'Ladin', 'roa': 'Romance languages', 'rup': 'Aromanian', 'mol': 'Moldavian',
            'mar': 'Marathi', 'guj': 'Gujarati', 'ori': 'Oriya', 'tam': 'Tamil',
            'mnp': 'Min Bei', 'cpx': 'Pu-Xian', 'czo': 'Min Zhong', 'csp': 'Southern Pinghua',
            'nap': 'Neapolitan', 'ast': 'Asturian', 'arg': 'Aragonese', 'ext': 'Extremaduran',
            'nya': 'Chichewa', 'sna': 'Shona', 'zul': 'Zulu', 'xho': 'Xhosa',
            'oci': 'Occitan', 'gsw': 'Swiss German', 'tur': 'Turkish', 'heb': 'Hebrew',
            'oss': 'Ossetian', 'che': 'Chechen', 'ava': 'Avar', 'kaa': 'Karakalpak',
            'roh': 'Romansh', 'frr': 'Northern Frisian', 'frs': 'Eastern Frisian',
            'san': 'Sanskrit', 'tib': 'Tibetan', 'mon': 'Mongolian', 'kaz': 'Kazakh',
            'snd': 'Sindhi', 'hin': 'Hindi', 'ben': 'Bengali', 'pan': 'Punjabi',
            'spa': 'Spanish', 'cat': 'Catalan', 'glg': 'Galician', 'eus': 'Basque',
            'srp': 'Serbian', 'mkd': 'Macedonian', 'bul': 'Bulgarian', 'ukr': 'Ukrainian',
            'ssw': 'Swati', 'ven': 'Venda', 'nbl': 'Ndebele', 'nso': 'Pedi',
            'tah': 'Tahitian', 'ton': 'Tongan', 'fij': 'Fijian', 'gil': 'Gilbertese',
            'tel': 'Telugu', 'kan': 'Kannada', 'mal': 'Malayalam', 'sin': 'Sinhala',
            'tgl': 'Tagalog', 'may': 'Malay', 'swa': 'Swahili', 'amh': 'Amharic',
            'tha': 'Thai', 'lao': 'Lao', 'mya': 'Burmese', 'khm': 'Khmer',
            'tir': 'Tigrinya', 'orm': 'Oromo', 'som': 'Somali', 'ber': 'Berber',
            'tpi': 'Tok Pisin', 'bis': 'Bislama', 'pis': 'Pijin', 'zom': 'Zomi',
            'vie': 'Vietnamese', 'jav': 'Javanese', 'ind': 'Indonesian', 'msa': 'Malay',
            'wxa': 'Waxianghua', 'czh': 'Huizhou', 'cdo': 'Min Dong', 'cjy': 'Jinyu',
            'zho': 'Chinese', 'nld': 'Dutch', 'swe': 'Swedish', 'fin': 'Finnish',
        }
        # Audio codec definitions
        self.codecs = {
            "01_dolbydigitalplus": ("digital+", "digitalplus", "ac3+", "e-ac3"),
            "02_dolbydigital": ("ac3", "dolbydigital"),
            "03_mp3": ("mp3", "mpeg-1 layer 3"),
            "04_wma": ("wma", "windows media audio"),
            "05_flac": ("flac", "free lossless audio codec"),
            "06_he-aac": ("he-aac", "aac+", "aac plus"),
            "07_aac": ("aac", "advanced audio coding"),
            "08_lpcm": ("lpcm", "linear pcm"),
            "09_dts-hd": ("dts-hd", "dts high definition"),
            "10_dts": ("dts", "digital theater systems"),
            "11_pcm": ("pcm", "pulse-code modulation"),
            "12_mpeg": ("mpeg", "mpeg audio"),
            "13_dolbytruehd": ("truehd", "dolby truehd"),
            "14_atmos": ("atmos", "dolby atmos"),
            "15_opus": ("opus",)
        }

        # Codec variants with channel configurations
        self.codec_info = {
            "dolbydigitalplus": ("51", "20", "71"),
            "dolbydigital": ("51", "20", "71"),
            "wma": ("8", "9"),
            "aac": ("20", "51"),
            "dts": ("51", "61", "71")
        }

        # Initialize converter type
        self.type, self.interesting_events = {
            "AudioIcon": (
                self.GET_AUDIO_ICON, (iPlayableService.evUpdatedInfo,)), "AudioCodec": (
                self.GET_AUDIO_CODEC, (iPlayableService.evUpdatedInfo,)), }.get(
            type, (self.GET_AUDIO_CODEC, (iPlayableService.evUpdatedInfo,)))

    def getAudio(self):
        """Get current audio track information"""
        try:
            service = self.source.service
            if not service:
                return False

            audio = service.audioTracks()
            if not audio:
                return False

            self.current_track = audio.getCurrentTrack()
            self.number_of_tracks = audio.getNumberOfTracks()

            if self.number_of_tracks > 0 and self.current_track > -1:
                self.audio_info = audio.getTrackInfo(self.current_track)
                return True

            return False
        except Exception as e:
            self.logger.error(f"Error getting audio info: {str(e)}")
            return False

    def getLanguage(self):
        """Get full language name from any format (code, abbreviation, etc.)"""
        try:
            if not hasattr(self, 'audio_info'):
                return ""

            raw_lang = self.audio_info.getLanguage()
            if not raw_lang:
                return "Undefined"

            # Clean the input
            clean_lang = raw_lang.strip().lower()

            # Check if it's already a full name
            if clean_lang.capitalize() in self.full_language_names.values():
                return clean_lang.capitalize()

            # Lookup in our comprehensive dictionary
            full_name = self.full_language_names.get(clean_lang)
            if full_name:
                return full_name

            # Try 3-letter codes if 2-letter lookup failed
            if len(clean_lang) == 3:
                # Try exact match first
                full_name = self.full_language_names.get(clean_lang)
                if full_name:
                    return full_name

                # Try case-insensitive match
                for code, name in self.full_language_names.items():
                    if len(code) == 3 and code.lower() == clean_lang:
                        return name

            # Final fallback - capitalize and return
            return clean_lang.capitalize() if clean_lang else ""

        except Exception as e:
            self.logger.warning(f"Error processing language: {str(e)}")
            return ""

    def getAudioCodec(self, info):
        """Get clean audio codec description with proper language handling"""
        if not self.getAudio():
            return _("unknown")

        description = (self.audio_info.getDescription() or "").strip()
        language = self.getLanguage()

        # Clean empty/unknown values
        description = "" if description.lower() in ("", "unknown") else description
        language = "" if language.lower() in ("", "unknown") else language

        # Special cases:
        # 1. If description contains language, return just description
        if language and language.lower() in description.lower():
            return description
        # 2. If description is a language code, replace with full name
        if description.lower() in self.full_language_names:
            return self.full_language_names[description.lower()]

        # Build clean output
        parts = []
        if description:
            parts.append(description)
        if language:
            parts.append(language)

        return " ".join(parts).strip() if parts else _("unknown")

    def getAudioIcon(self, info):
        """Get simplified audio codec name for icon display"""
        try:
            codec_name = self.getAudioCodec(info)
            # Clean the codec name for matching
            clean_name = codec_name.translate(
                str.maketrans("", "", " .()")).lower()
            return self._match_audio_codec(clean_name)
        except Exception as e:
            self.logger.error(f"Error getting audio icon: {str(e)}")
            return "unknown"

    def _match_audio_codec(self, audio_name):
        """Match audio name to known codecs and variants"""
        for return_codec, codecs in sorted(self.codecs.items()):
            for codec in codecs:
                if codec in audio_name:
                    base_codec = return_codec.split('_')[1]

                    # Check for channel configurations
                    if base_codec in self.codec_info:
                        for variant in self.codec_info[base_codec]:
                            if variant in audio_name:
                                return f"{base_codec}{variant}"

                    return base_codec

        return audio_name

    @cached
    def getText(self):
        """Main method to get requested audio information"""
        try:
            service = self.source.service
            if not service:
                return _("No service")

            info = service.info()
            if not info:
                return _("No info")

            if self.type == self.GET_AUDIO_CODEC:
                return self.getAudioCodec(info)
            elif self.type == self.GET_AUDIO_ICON:
                return self.getAudioIcon(info)

        except Exception as e:
            self.logger.error(f"Error in getText: {str(e)}")

        return _("Unknown")

    text = property(getText)

    def changed(self, what):
        """Handle change events"""
        if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
            Converter.changed(self, what)

    def destroy(self):
        """Clean up resources"""
        self.poll_enabled = False
        super().destroy()


# Usage Examples:
# Basic Audio Codec Display:
"""
<widget source="session.CurrentService" render="Label" position="100,100" size="200,25" font="Regular;18">
    <convert type="AglareAudioInfo">AudioCodec</convert>
</widget>
"""
# Audio Icon Display:

"""
<widget source="session.CurrentService" render="Pixmap" position="100,130" size="30,30">
    <convert type="AglareAudioInfo">AudioIcon</convert>
    <convert type="ConditionalShowHide"/>
</widget>
"""
# Combined Audio Info Panel:

"""
<panel position="100,100" size="300,60" backgroundColor="#40000000">
    <widget source="session.CurrentService" render="Pixmap" position="10,10" size="40,40">
        <convert type="AglareAudioInfo">AudioIcon</convert>
        <convert type="ConditionalShowHide"/>
    </widget>
    <widget source="session.CurrentService" render="Label" position="60,15" size="230,30" font="Regular;16">
        <convert type="AglareAudioInfo">AudioCodec</convert>
    </widget>
</panel>
"""
