import requests
import logging
from datetime import datetime, timedelta
from config import ODDS_API_KEY, ODDS_API_BASE_URL, SPORTS_LIST
from pytz import timezone

logger = logging.getLogger(__name__)

# USA timezone
USA_TZ = timezone('America/New_York')


class OddsAPIHandler:
    def __init__(self):
        self.api_key = ODDS_API_KEY
        self.base_url = ODDS_API_BASE_URL

    def get_live_matches(self, sport="americanfootball_nfl"):
        """
        Fetch LIVE matches from The Odds API (USA sports)
        """
        try:
            url = f"{self.base_url}/sports/{sport}/odds"
            params = {
                "apiKey": self.api_key,
                "regions": "us",  # USA regions
                "markets": "h2h,spreads,totals",  # American odds markets
                "oddsFormat": "american"  # American odds format
            }
            
            logger.info(f"Fetching live matches for {sport}...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            matches = []
            
            if not data:
                logger.warning(f"No live matches found for {sport}")
                return []
            
            for event in data[:8]:  # Limit to 8 matches
                try:
                    match = {
                        "match_id": event["id"],
                        "sport": sport,
                        "home_team": event["home_team"],
                        "away_team": event["away_team"],
                        "commence_time": event["commence_time"],
                        "bookmakers": event.get("bookmakers", []),
                        "status": "live"
                    }
                    matches.append(match)
                    logger.debug(f"Added match: {match['home_team']} vs {match['away_team']}")
                except KeyError as e:
                    logger.error(f"Missing field in match data: {e}")
                    continue
            
            logger.info(f"✅ Fetched {len(matches)} live matches")
            return matches
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching live matches: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error in get_live_matches: {e}")
            return []

    def get_upcoming_matches(self, sport="americanfootball_nfl", days=7):
        """
        Fetch UPCOMING matches for the next N days
        """
        try:
            url = f"{self.base_url}/sports/{sport}/odds"
            params = {
                "apiKey": self.api_key,
                "regions": "us",  # USA regions
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american",
                "dateFormat": "iso"
            }
            
            logger.info(f"Fetching upcoming matches for {sport} (next {days} days)...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            matches = []
            
            now = datetime.now(USA_TZ)
            cutoff_date = now + timedelta(days=days)
            
            if not data:
                logger.warning(f"No upcoming matches found for {sport}")
                return []
            
            for event in data[:8]:  # Limit to 8 matches
                try:
                    commence_time = datetime.fromisoformat(
                        event["commence_time"].replace("Z", "+00:00")
                    ).astimezone(USA_TZ)
                    
                    # Filter by date range
                    if commence_time <= cutoff_date:
                        match = {
                            "match_id": event["id"],
                            "sport": sport,
                            "home_team": event["home_team"],
                            "away_team": event["away_team"],
                            "commence_time": event["commence_time"],
                            "bookmakers": event.get("bookmakers", []),
                            "status": "upcoming"
                        }
                        matches.append(match)
                        logger.debug(f"Added upcoming match: {match['home_team']} vs {match['away_team']}")
                except (KeyError, ValueError) as e:
                    logger.error(f"Error processing match: {e}")
                    continue
            
            logger.info(f"✅ Fetched {len(matches)} upcoming matches")
            return matches
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching upcoming matches: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error in get_upcoming_matches: {e}")
            return []

    def get_match_odds(self, match_id, sport="americanfootball_nfl"):
        """
        Get detailed odds for a specific match
        """
        try:
            url = f"{self.base_url}/sports/{sport}/odds"
            params = {
                "apiKey": self.api_key,
                "regions": "us",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "american",
                "eventIds": match_id
            }
            
            logger.info(f"Fetching odds for match {match_id}...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No odds data found for match {match_id}")
                return None
            
            event = data[0]
            odds_data = {
                "match_id": match_id,
                "home_team": event["home_team"],
                "away_team": event["away_team"],
                "commence_time": event["commence_time"],
                "odds": [],
                "spreads": [],
                "totals": []
            }
            
            # Extract odds from bookmakers
            for bookmaker in event.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market["key"] == "h2h":
                        for outcome in market.get("outcomes", []):
                            odds_data["odds"].append({
                                "team": outcome["name"],
                                "odds": outcome["price"],
                                "bookmaker": bookmaker.get("title", "Unknown")
                            })
                    elif market["key"] == "spreads":
                        for outcome in market.get("outcomes", []):
                            odds_data["spreads"].append({
                                "team": outcome["name"],
                                "spread": outcome.get("point", 0),
                                "odds": outcome["price"]
                            })
                    elif market["key"] == "totals":
                        for outcome in market.get("outcomes", []):
                            odds_data["totals"].append({
                                "type": outcome["name"],
                                "point": outcome.get("point", 0),
                                "odds": outcome["price"]
                            })
            
            logger.info(f"✅ Fetched odds for {odds_data['home_team']} vs {odds_data['away_team']}")
            return odds_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching match odds: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error in get_match_odds: {e}")
            return None

    def get_sports_list(self):
        """
        Get list of available USA sports
        """
        try:
            url = f"{self.base_url}/sports"
            params = {"apiKey": self.api_key}
            
            logger.info("Fetching available sports...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            sports = []
            
            # Filter only active USA sports
            usa_sports_keys = [s for s in SPORTS_LIST if "american" in s or "nba" in s or "mlb" in s or "nhl" in s or "mls" in s]
            
            for sport in data:
                if not sport["inactive"] and sport["key"] in usa_sports_keys:
                    sports.append({
                        "key": sport["key"],
                        "name": sport["title"],
                        "group": sport["group"],
                        "active": not sport["inactive"]
                    })
                    logger.debug(f"Added sport: {sport['title']}")
            
            logger.info(f"✅ Found {len(sports)} USA sports")
            return sports
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching sports list: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error in get_sports_list: {e}")
            return []

    def format_match_display(self, match):
        """
        Format match data for display in Telegram
        """
        try:
            commence = datetime.fromisoformat(match["commence_time"].replace("Z", "+00:00"))
            commence_str = commence.astimezone(USA_TZ).strftime("%m/%d %H:%M ET")
        except:
            commence_str = match["commence_time"]
        
        display = f"""
🏆 <b>{match['home_team']} vs {match['away_team']}</b>
⏰ {commence_str}
"""
        
        # Add odds summary
        if match.get("bookmakers"):
            bookmaker = match["bookmakers"][0]
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h":
                    display += "\n📊 <b>Odds:</b>\n"
                    for outcome in market.get("outcomes", []):
                        odds = outcome['price']
                        display += f"  • {outcome['name']}: <b>{odds:+.0f}</b>\n"
        
        return display

    def format_odds_display(self, odds_data):
        """
        Format odds data for display in Telegram
        """
        if not odds_data:
            return "❌ Odds data not available"
        
        try:
            commence = datetime.fromisoformat(odds_data["commence_time"].replace("Z", "+00:00"))
            commence_str = commence.astimezone(USA_TZ).strftime("%m/%d %H:%M ET")
        except:
            commence_str = odds_data["commence_time"]
        
        display = f"""
⚽ <b>{odds_data['home_team']} vs {odds_data['away_team']}</b>
⏰ {commence_str}

📊 <b>Moneyline Odds:</b>
"""
        
        for odd in odds_data.get("odds", []):
            display += f"  • {odd['team']}: <b>{odd['odds']:+.0f}</b>\n"
        
        if odds_data.get("spreads"):
            display += "\n📈 <b>Point Spread:</b>\n"
            for spread in odds_data.get("spreads", []):
                display += f"  • {spread['team']} {spread['spread']:+.1f}: <b>{spread['odds']:+.0f}</b>\n"
        
        if odds_data.get("totals"):
            display += "\n🎯 <b>Over/Under:</b>\n"
            for total in odds_data.get("totals", []):
                display += f"  • {total['type']} {total['point']}: <b>{total['odds']:+.0f}</b>\n"
        
        return display


# Initialize API handler
odds_api = OddsAPIHandler()
