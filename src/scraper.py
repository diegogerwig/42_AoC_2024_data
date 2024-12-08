import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import traceback

class AOCScraper:
    def __init__(self):
        self.url = "https://aoc.42barcelona.com/ranking/es"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def _process_row(self, row) -> Optional[Dict]:
        """Process a single row of data."""
        try:
            cells = row.find_all('td')
            if len(cells) < 5:
                return None

            # Basic data
            data = {
                'login': cells[0].text.strip(),
                'campus': cells[1].text.strip(),
                'streak': int(cells[2].text.strip()),
                'points': float(cells[3].text.strip()),
            }

            # Initialize counters
            completed_days = 0
            gold_stars = 0
            silver_stars = 0

            # Process stars day by day
            star_cells = cells[4:]
            for i, cell in enumerate(star_cells):
                day_num = i + 1
                
                # Get all star spans
                spans = cell.find_all('span')
                
                # Count gold and silver stars separately
                day_gold = len(cell.find_all('span', class_='star1'))  # Oro
                day_silver = len(cell.find_all('span', class_='star0'))  # Plata
                
                # Limitar a máximo 2 estrellas por tipo
                day_gold = min(day_gold, 2)
                day_silver = min(day_silver, 2)
                
                # Actualizar contadores totales
                gold_stars += day_gold
                silver_stars += day_silver
                
                # Update completed days if any stars were earned
                if (day_gold + day_silver > 0) and day_num > completed_days:
                    completed_days = day_num
                
                # Store total stars for the day (max 2)
                data[f'day_{day_num}'] = min(day_gold + day_silver, 2)

            # Add star totals
            data['completed_days'] = completed_days
            data['gold_stars'] = gold_stars
            data['silver_stars'] = silver_stars
            data['total_stars'] = gold_stars + silver_stars

            return data
            
        except Exception as e:
            st.error(f"Error processing row: {str(e)}")
            return None

    def _convert_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert numeric columns to their proper type."""
        numeric_cols = ['streak', 'points', 'completed_days', 
                       'gold_stars', 'silver_stars', 'total_stars']
        day_cols = [col for col in df.columns if col.startswith('day_')]
        numeric_cols.extend(day_cols)
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                # Keep points as float, convert others to int
                if col != 'points':
                    df[col] = df[col].astype(int)
        
        return df

    def scrape_data(self) -> pd.DataFrame:
        """Scrape AOC rankings data."""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            table = soup.find('table', id='rankingTable')
            if not table:
                st.error("No se encontró la tabla de ranking")
                return pd.DataFrame()

            tbody = table.find('tbody')
            if not tbody:
                st.error("No se encontró el cuerpo de la tabla")
                return pd.DataFrame()

            data = []
            for row in tbody.find_all('tr'):
                row_data = self._process_row(row)
                if row_data:
                    data.append(row_data)

            if not data:
                st.error("No se encontraron datos")
                return pd.DataFrame()

            df = pd.DataFrame(data)
            df = self._convert_numeric_columns(df)
            return df.sort_values('points', ascending=False).reset_index(drop=True)
            
        except Exception as e:
            st.error(f"Error scraping data: {str(e)}")
            st.write("Traceback:", traceback.format_exc())
            return pd.DataFrame()

    def get_column_descriptions(self) -> Dict[str, str]:
        """Get descriptions for all columns."""
        return {
            'login': 'User login name',
            'campus': 'Campus name',
            'streak': 'Current streak of consecutive days completed',
            'points': 'Total points earned',
            'completed_days': 'Highest day number with at least one star',
            'gold_stars': 'Total number of gold stars',
            'silver_stars': 'Total number of silver stars',
            'total_stars': 'Total number of stars (gold + silver, max 2 per day)',
            **{f'day_{i}': f'Day {i} total stars (0-2, can be gold or silver)' 
               for i in range(1, 26)}
        }