import streamlit as st
import requests
import pandas as pd
import mysql.connector

# Connect to MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="password",
    database="myDB"
)
cursor = db.cursor()

# Function to authenticate users
def authenticate(username, password):
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    user = cursor.fetchone()
    return user is not None

def register(username, password):
    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
    db.commit()
    st.success("Registration successful")

st.title('World Football Leagues Dashboard')
st.sidebar.title('Widget Section')

headers = {'X-Auth-Token': '14cd47abf226485cb379005e381b0705'}

def fetch_data1():
    url = "http://api.football-data.org/v2/competitions/"
    response = requests.request("GET", url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.write(f"Error fetching data: {response.status_code}")
        st.write(response.text)
        return None

def extract_winner(match):
    score = match.get('score', {})
    if 'winner' in score:
        winner = score['winner']
        return winner.capitalize().replace('_', ' ')
    else:
        return 'No Result'

def extract_match_info(matches):
    data = []
    for match in matches:
        home_score = match['score']['fullTime']['homeTeam'] if match['score']['fullTime']['homeTeam'] is not None else 0
        away_score = match['score']['fullTime']['awayTeam'] if match['score']['fullTime']['awayTeam'] is not None else 0
        
        match_info = {
            'Home Team': match['homeTeam']['name'],
            'Away Team': match['awayTeam']['name'],
            'Date': match['utcDate'],
            'Status': match['status'],
            'Referee': match['referees'][0]['name'] if match['referees'] else 'Unknown',
            'Winner': extract_winner(match),
            'Score': f"{home_score}-{away_score}"
        }
        data.append(match_info)
    return data

def fetch_team_matches(team_id, date_from=None, date_to=None, season=None, competitions=None, status=None, venue=None, limit=None):
    base_url = f"https://api.football-data.org/v4/teams/{team_id}/matches/"
    params = {
        'dateFrom': date_from,
        'dateTo': date_to,
        'season': season,
        'competitions': competitions,
        'status': status,
        'venue': venue,
        'limit': limit
    }
    response = requests.get(base_url, headers=headers, params=params)
    if response.status_code == 200:
        matches_data = response.json()
        if 'matches' in matches_data:
            return pd.json_normalize(matches_data['matches'])
        else:
            return None
    else:
        return None

def fetch_match_schedules_data(competition_id, matchday):
    base_url = f"http://api.football-data.org/v2/competitions/{competition_id}/matches"
    params = {'matchday': matchday}
    
    response = requests.get(base_url, headers=headers, params=params)
    return response.json()

def fetch_teams():
    url = "https://api.football-data.org/v2/teams"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        teams_data = response.json()
        teams_df = pd.json_normalize(teams_data['teams'])
        return teams_df[['name', 'id']]
    else:
        return None

def flatten_current_team(data):
    current_team = data.pop('currentTeam')
    data.update(current_team['area'])
    data['currentTeam_id'] = current_team['id']
    data['currentTeam_name'] = current_team['name']
    data['currentTeam_shortName'] = current_team['shortName']
    data['currentTeam_tla'] = current_team['tla']
    data['currentTeam_crest'] = current_team['crest']
    data['currentTeam_address'] = current_team['address']
    data['currentTeam_website'] = current_team['website']
    data['currentTeam_founded'] = current_team['founded']
    data['currentTeam_clubColors'] = current_team['clubColors']
    data['currentTeam_venue'] = current_team['venue']
    data['currentTeam_runningCompetitions'] = current_team['runningCompetitions']
    data['currentTeam_contract_start'] = current_team['contract']['start']
    data['currentTeam_contract_until'] = current_team['contract']['until']
    return data

def main():
    st.sidebar.title("Authentication")
    choice = st.sidebar.radio("Menu", ["Login", "Register"])

    if choice == "Login":
        st.title("User Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if authenticate(username, password):
                st.success("Login successful")
                data1 = fetch_data1()

                area_dict = {}
                comp_dict = {}

                if data1:
                    for i in range(len(data1['competitions'])):
                        area_dict[data1['competitions'][i]['area']['name']] = 0
                        comp_dict[data1['competitions'][i]['name']] = 0

                    for i in range(len(data1['competitions'])):
                        area_dict[data1['competitions'][i]['area']['name']] += 1
                        comp_dict[data1['competitions'][i]['name']] += 1

                    area_df = pd.DataFrame(area_dict.items(), columns=['Country Name', 'Count'])
                    comp_df = pd.DataFrame(comp_dict.items(), columns=['League Name','Count'])

                    st.write("### Country-wise League Counts")
                    st.dataframe(area_df, height=800 , width=800)

                    st.write("### League-wise Count")
                    st.dataframe(comp_df, height=800 , width=800)

                # Standings data
                st.write("## Standings Data")
                st.sidebar.title('Select Options')

                # Sidebar inputs for match schedules
                competition_id = st.sidebar.text_input('Enter Competition ID (e.g., PL for Premier League):')
                matchday = st.sidebar.number_input('Enter Matchday:', min_value=1)

                # Fetch match schedules data based on user input
                if competition_id:
                    match_schedules_data = fetch_match_schedules_data(competition_id, matchday)

                    # Display the fetched match schedules data
                    if match_schedules_data and 'matches' in match_schedules_data:
                        # Extract relevant match information
                        match_info = extract_match_info(match_schedules_data['matches'])
                        
                        # Convert extracted data to DataFrame
                        df = pd.DataFrame(match_info)
                        
                        # Display DataFrame
                        st.write("### Match Schedules Data")
                        st.dataframe(df)
                    else:
                        st.write("No match schedules data available for the specified input.")
                else:
                    st.write("Please enter a Competition ID.")

                # Fetch and display teams
                teams_df = fetch_teams()
                if teams_df is not None:
                    team_names = teams_df['name'].tolist()
                    selected_team = st.sidebar.selectbox('Select Team:', team_names)
                    team_id = teams_df[teams_df['name'] == selected_team]['id'].iloc[0]
                else:
                    st.sidebar.write("No teams data available.")

                status = st.sidebar.selectbox('Select Match Status:', ['SCHEDULED', 'FINISHED', 'POSTPONED', 'CANCELED', 'IN_PLAY', 'PAUSED'])

                # Button to fetch matches
                if st.sidebar.button('Fetch Matches'):
                    # Fetch team's matches based on filters
                    matches_df = fetch_team_matches(team_id, status=status)
                    
                    # Display the fetched matches data
                    if matches_df is not None:
                        st.write("### Matches Data")
                        st.dataframe(matches_df)
                    else:
                        st.write("No matches data available for the specified filters.")
            else:
                st.error("Invalid username or password")

    elif choice == "Register":
        st.title("User Registration")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Register"):
            register(username, password)

if __name__ == "__main__":
    main()
