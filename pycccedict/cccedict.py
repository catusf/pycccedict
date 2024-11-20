"""CC-CEDICT."""

import gzip
from pathlib import Path
from typing import Dict, List, Optional, TextIO, Union
from datetime import datetime

DATA_PATH = Path(__file__).parent / 'data' / 'cedict_1_0_ts_utf-8_mdbg.txt.gz'
TMP_PATH = Path(__file__).parent / 'data' / 'tmp-cedict_1_0_ts_utf-8_mdbg.txt.gz' # Uses for updating data
DATA_URL = r"https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"

class CcCedict:
    """CC-CEDICT."""

    def __init__(self) -> None:
        path = DATA_PATH
        self._data_datetime = None
        
        with gzip.open(path, mode='rt', encoding='utf-8') as file:
            self._parse_file(file)

    def get_data_datetime(self) -> datetime:
        """Gets the definition data file datetime.
        """
        return self._data_datetime

    def get_data_days_old(self) -> int:
        """Gets how many day old is the definition data file.
        
            This can be used to decide if an update is due and call update_cedict()
        """
        
        if not self._data_datetime: # Data date not obtained
             raise ValueError("Data datetime is not set.")
            
        # Get the current date
        current_date = datetime.utcnow()
        
        # Calculate the difference in years
        difference = current_date - self._data_datetime 
        
        # Check if the difference is one year or more
        return difference.days

    def update_cedict(self) -> bool:
        """
        Downloads the CEDICT file to a temporary file. If successful, overwrites the old datafile.

        Returns:
            bool: True if the file is successfully downloaded and moved, False otherwise.
        """

        # Imports here not to litters normal uses of packages
        import requests
        from pathlib import Path
        import shutil

        try:
            # Download the file to the temporary directory
            print(f"Downloading file from {DATA_URL} to {TMP_PATH}...")
            response = requests.get(DATA_URL, stream=True)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)

            with open(TMP_PATH, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            print("Download succeeded. Moving file to data directory...")

            # Move the file to the data directory
            shutil.move(TMP_PATH, DATA_PATH)
            print(f"Data successfully updated to {DATA_PATH}")

            return True
        except requests.RequestException as e:
            print(f"Error downloading the file: {e}")
        except IOError as e:
            print(f"Error moving the file: {e}")

        # Clean up temporary file if it exists
        if TMP_PATH.exists():
            try:
                TMP_PATH.unlink()
            except Exception as e:
                print(f"Error cleaning up temporary file: {e}")

        return False

    def get_definitions(self, chinese: str) -> Optional[List]:
        """Gets definitions."""
        return self._get_field(field='definitions', chinese=chinese)

    def get_pinyin(self, chinese: str) -> Optional[str]:
        """Gets pinyin."""
        return self._get_field(field='pinyin', chinese=chinese)

    def get_simplified(self, chinese: str) -> Optional[str]:
        """Gets simplified."""
        return self._get_field(field='simplified', chinese=chinese)

    def get_traditional(self, chinese: str) -> Optional[str]:
        """Gets traditional."""
        return self._get_field(field='traditional', chinese=chinese)

    def get_entry(self, chinese: str) -> Optional[Dict]:
        """Gets an entry."""
        # Check simplified.
        if chinese in self.simplified_to_index:
            i = self.simplified_to_index[chinese]
            return self.entries[i]

        # Check traditional.
        if chinese in self.traditional_to_index:
            i = self.traditional_to_index[chinese]
            return self.entries[i]

        return None

    def get_entries(self) -> List:
        """Gets all entries."""
        return self.entries

    def _get_field(self, field: str, chinese: str) -> Union[str, List, None]:
        """Gets field."""
        entry = self.get_entry(chinese)
        if entry is None:
            return None

        return entry[field]

    def _parse_file(self, file: TextIO) -> None:
        self.entries = []
        self.simplified_to_index = {}
        self.traditional_to_index = {}
        i = 0

        for line in file:
            entry = self._parse_line(line)
            if entry is None:
                continue

            # Add entry.
            self.entries.append(entry)

            # Share entries for simplified and traditional.
            simplified = entry['simplified']
            traditional = entry['traditional']
            self.simplified_to_index[simplified] = i
            self.traditional_to_index[traditional] = i
            i += 1

    def _parse_line(self, line: str) -> Optional[Dict]:
        # Skip comments.
        if line.startswith('#'):
            DATE_TAG = "#! date="
            
            if line.startswith(DATE_TAG): # Example "#! date=2024-11-18T23:06:27Z"
                self._data_datetime = datetime.strptime(line[len(DATE_TAG):].strip(), "%Y-%m-%dT%H:%M:%SZ")                
                
            return None

        # Strip whitespace and trailing slash.
        line = line.strip()
        line = line.rstrip('/')

        # Get chinese parts.
        chinese, english = line.split('/', maxsplit=1)
        chinese = chinese.strip()
        traditional_and_simplified, pinyin = chinese.split('[')
        traditional_and_simplified = traditional_and_simplified.strip()
        traditional, simplified = traditional_and_simplified.split()

        # Remove brackets around pinyin.
        pinyin = pinyin[:-1]

        # Get english definitions.
        senses = english.split('/')
        glosses = [sense.split(';') for sense in senses]
        definitions = [definition for gloss in glosses for definition in gloss]

        return {
            'traditional': traditional,
            'simplified': simplified,
            'pinyin': pinyin,
            'definitions': definitions,
        }
