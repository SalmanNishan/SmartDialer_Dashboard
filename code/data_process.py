from config import base_url, client_mapping
import pandas as pd

def url_fixer(url):
    link = url.split('/')[3]
    new_url = base_url + link
    return new_url

def client_data(client_numbers):
    '''
    Extract and Fomat Client Numbers from CurePulse
    '''
    new_client_numbers = []
    for original_number in client_numbers:

        number = str(original_number)

        if len(number) == 10:
            new_client_numbers.append('+1' + number)
        elif len(number) == 11:
            new_client_numbers.append('+' + number)
        elif len(number) == 12:
            new_client_numbers.append(number)
        elif len(number) == 15:
            new_client_numbers.append(number[4:])
        else:
            new_client_numbers.append(number)
    
    return new_client_numbers

def dict_maker(numbers, names):
    '''
   Creates mapping dict
    '''
    mydict = {}
    for i in range(len(numbers)):
        mydict[numbers[i]] = names[i]
    return mydict

def client_number_to_name_mapper(original_number):
    '''
    Maps client numbers to names
    '''
    df = pd.read_csv(client_mapping)

    number = str(original_number)

    if len(number) == 10:
        new_number = '+1' + number
    elif len(number) == 11:
        new_number = '+' + number
    elif len(number) == 12:
        new_number = number
    elif len(number) == 15:
        new_number = number[4:]
    else:
        new_number = number
    
    client_numbers = client_data(df['Client Numbers'].values)
    client_names = df['Client Names'].values

    client_mappings = dict_maker(client_numbers, client_names)

    if new_number in client_mappings:
        return client_mappings[new_number]
    else:
        return 'Client'
    
def format_talk_time(talk_time_seconds):
    talk_time_minutes = int(talk_time_seconds) // 60
    remaining_talk_time_seconds = int(talk_time_seconds) % 60
    if talk_time_minutes >= 60: 
        talk_time_hours = int(talk_time_minutes) // 60
        total_duration = f"{talk_time_hours}:{talk_time_minutes}:{remaining_talk_time_seconds:02d}"
    else:
        total_duration = f"{talk_time_minutes}:{remaining_talk_time_seconds:02d}"
    return total_duration

def create_document(filename, required_date, call_duration, processed_audio_duration, processed_agent_duration, processed_client_duration, transcriptions, agent_name, client_id, client_name, call_type, processed_audio_file, processed_agent_file, processed_client_file):
    document = {
        'Filename': filename,
        'Date': required_date,
        'Call_Duration': call_duration,
        'Processed_Audio_Duration': processed_audio_duration,
        'Processed_Agent_Duration': processed_agent_duration,
        'Processed_Client_Duration': processed_client_duration,
        'Transcription': transcriptions, 
        'client_id': client_id,
        'client_name': client_name,
        'agent_name': agent_name,
        'call_type': call_type,
        "audio_file": processed_audio_file,
        "agent_audio_file": processed_agent_file,
        "client_audio_file": processed_client_file
        }
    return document