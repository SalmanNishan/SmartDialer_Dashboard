import os
import json
import shutil
import requests
from tqdm import tqdm
import soundfile as sf
from pydub import AudioSegment
from pymongo import MongoClient
from datetime import datetime, timedelta

from config import *
from music_remover import remove_music
from transcription import get_transcriptions
from data_process import url_fixer, client_number_to_name_mapper, format_talk_time, create_document

client = MongoClient(mongo_url)
db = client[db_name]
collection = db[collection_name]

current_time = datetime.now()
cutoff_time = current_time.replace(hour=17, minute=30, second=0, microsecond=0)
if current_time < cutoff_time:
    adjusted_date = current_time - timedelta(days=1)
else:
    adjusted_date = current_time
required_date = adjusted_date.strftime('%Y-%m-%d')
# required_date = "2024-09-26"
print("record_fetching_date", required_date)

voip_link_date = required_date[2:]
# rcm_extensions = ['122', '123', '126', '168', '175', '183', '332', '343', '389', '408', '410', '427', '431', '436', '443', '454', '455', '460', '463', '466', '468', '473', '476', '480', 
#                   '481', '486', '528', '535', '536', '543', '557', '566', '582', '630', '631', '634', '635', '644', '646', '761', '762', '789', '794', '796', '818', '819', '834', '853', 
#                   '855', '869', '902', '913', '914', '921', '922', '923', '929', '932', '934', '939', '950', '952', '957', '969', '972', '973', '977', '978', '979', '982', '983', '989', 
#                   '1014', '1053', '1059', '1075', '1076', '1079', '1080', '1086', '1089', '1093', '1095', '1096', '1097', '1100', '1101', '1103', '1104', '1112', '1115', '1117', '1128', 
#                   '1130', '1131', '1132', '1133', '1137', '1145', '1146', '1147', '1151', '1152', '1156', '1159', '1160', '1161', '1178', '1180', '1183', '1184', '1185', '1186', '1191', 
#                   '1193', '1194', '1196', '1202', '1203', '1208', '1210', '1213', '1216', '1217', '1218', '1219', '1235', '1236', '1251', '1256', '1260', '1262', '1263', '1270', '1281', 
#                   '1290', '1338', '1343', '1346', '1348', '1363', '1364', '1365', '1366', '1379', '1388', '1391', '1396', '1398', '1403', '1404', '1407', '1409', '1411', '1419', '1429', 
#                   '1430', '1440', '1441', '1450', '1452', '1471', '1474', '1488', '1495', '1500', '2222', '5509', '5510']
# rcm_extensions = ["347", "1011"]
rcm_extensions = ["1011", "104", "1175", "1138"]

target_dir = os.path.join(calls_directory, required_date)
if not os.path.exists(target_dir):
    os.makedirs(target_dir)

processed_dir = os.path.join(processed_calls_directory, required_date)
if not os.path.exists(processed_dir):
    os.makedirs(processed_dir)

already_downloaded_files_list = os.listdir(target_dir)

updated_voip_url_incoming = voip_url + voip_link_date + incoming
response_API = requests.get(updated_voip_url_incoming)
data = response_API.text
response = json.loads(data)
with open(f'{voip_data_path}/incoming_{required_date}.json', 'w') as file:
    json.dump(response, file)
list_records = response['data']

for record in tqdm(list_records):
    if record['call_to'] in rcm_extensions:
        if int(record['talk_time']) >= 60:
            print("processing started")

            # Fetching URLs
            url = url_fixer(record['recording'])  # url of the audio file
            agent_url = url_fixer(record['agent_recording'])  # url of the agent's audio file
            client_url = url_fixer(record['client_recording'])  # url of the client's audio file

            # Creating filenames for saving audio
            filename = record['call_id'] + '.wav'
            print("filename", filename)
            agent_filename = "agent_" + filename
            client_filename = "client_" + filename

            existing_document = list(collection.find({'Filename': filename}))
            if existing_document:
                if filename == existing_document[0]['Filename']:
                    continue

            # Check if files are already downloaded
            if filename not in already_downloaded_files_list:
                # Saving the audio files
                save_path = os.path.join(target_dir, filename)
                r = requests.get(url, allow_redirects=True)
                open(save_path, 'wb').write(r.content)  # Save audio file

                save_path = os.path.join(target_dir, agent_filename)
                r = requests.get(agent_url, allow_redirects=True)
                open(save_path, 'wb').write(r.content)  # Save agent audio file

                save_path = os.path.join(target_dir, client_filename)
                r = requests.get(client_url, allow_redirects=True)
                open(save_path, 'wb').write(r.content)  # Save client audio file

            # Fetching client and agent names
            client_number = record['call_from']
            client_name = client_number_to_name_mapper(client_number)
            agent_name = record['agent_name']

            # Fetching the audio files
            audio_file = os.path.join(target_dir, filename)
            agent_file = os.path.join(target_dir, agent_filename)
            client_file = os.path.join(target_dir, client_filename)

            audio_music_removed, speech_segments, audio_length = remove_music(audio_file, music_model_path)
            agent_music_removed, _, total_agent_duration = remove_music(agent_file, music_model_path, agent=True)
            client_music_removed, _, total_client_duration = remove_music(client_file, music_model_path)

            sf.write(os.path.join(processed_dir, filename), audio_music_removed, samplerate=16000, format='WAV')
            sf.write(os.path.join(processed_dir, agent_filename), agent_music_removed, samplerate=16000, format='WAV')
            sf.write(os.path.join(processed_dir, client_filename), client_music_removed, samplerate=16000, format='WAV')
            
            processed_audio_file = os.path.join(processed_dir, filename)
            processed_agent_file = os.path.join(processed_dir, agent_filename)
            processed_client_file = os.path.join(processed_dir, client_filename)

            total_duration = format_talk_time(record["talk_time"])
            processed_audio_duration = format_talk_time(AudioSegment.from_file(processed_audio_file).duration_seconds)
            processed_agent_duration = format_talk_time(AudioSegment.from_file(processed_agent_file).duration_seconds)
            processed_client_duration = format_talk_time(AudioSegment.from_file(processed_client_file).duration_seconds)
            call_type = "Incoming"

            if processed_audio_duration >= "30" and processed_agent_duration >= "30" and processed_client_duration >= "30":
                final_transcription = get_transcriptions(agent_name, client_name, processed_audio_file, processed_agent_file, processed_client_file)
                document = create_document(filename, required_date, total_duration, processed_audio_duration, processed_agent_duration, processed_client_duration, final_transcription, agent_name, client_number, client_name, call_type, processed_audio_file, processed_agent_file, processed_client_file)
                insert_result = collection.insert_one(document)
                print("document_inserted")

updated_voip_url_outgoing = voip_url + voip_link_date + outgoing
response_API = requests.get(updated_voip_url_outgoing)
data = response_API.text
response = json.loads(data)
with open(f'{voip_data_path}/outgoing_{required_date}.json', 'w') as file:
    json.dump(response, file)
list_records = response['data']

for record in tqdm(list_records):
    if record['call_from'] in rcm_extensions:
        if int(record['talk_time']) >= 60:
            print("processing started")

            # Fetching URLs
            url = url_fixer(record['recording'])  # url of the audio file
            agent_url = url_fixer(record['agent_recording'])  # url of the agent's audio file
            client_url = url_fixer(record['client_recording'])  # url of the client's audio file

            # Creating filenames for saving audio
            filename = record['call_id'] + '.wav'
            print("filename", filename)
            agent_filename = "agent_" + filename
            client_filename = "client_" + filename

            existing_document = list(collection.find({'Filename': filename}))
            if existing_document:
                if filename == existing_document[0]['Filename']:
                    continue

            # Check if files are already downloaded
            if filename not in already_downloaded_files_list:
                # Saving the audio files
                save_path = os.path.join(target_dir, filename)
                r = requests.get(url, allow_redirects=True)
                open(save_path, 'wb').write(r.content)  # Save audio file

                save_path = os.path.join(target_dir, agent_filename)
                r = requests.get(agent_url, allow_redirects=True)
                open(save_path, 'wb').write(r.content)  # Save agent audio file

                save_path = os.path.join(target_dir, client_filename)
                r = requests.get(client_url, allow_redirects=True)
                open(save_path, 'wb').write(r.content)  # Save client audio file

            # Fetching client and agent names
            client_number = record['call_to']
            client_name = client_number_to_name_mapper(client_number)
            agent_name = record['caller_name']

            # Fetching the audio files
            audio_file = os.path.join(target_dir, filename)
            agent_file = os.path.join(target_dir, agent_filename)
            client_file = os.path.join(target_dir, client_filename)

            audio_music_removed, speech_segments, audio_length = remove_music(audio_file, music_model_path)
            agent_music_removed, _, total_agent_duration = remove_music(agent_file, music_model_path, agent=True)
            client_music_removed, _, total_client_duration = remove_music(client_file, music_model_path)

            sf.write(os.path.join(processed_dir, filename), audio_music_removed, samplerate=16000, format='WAV')
            sf.write(os.path.join(processed_dir, agent_filename), agent_music_removed, samplerate=16000, format='WAV')
            sf.write(os.path.join(processed_dir, client_filename), client_music_removed, samplerate=16000, format='WAV')
            
            processed_audio_file = os.path.join(processed_dir, filename)
            processed_agent_file = os.path.join(processed_dir, agent_filename)
            processed_client_file = os.path.join(processed_dir, client_filename)

            total_duration = format_talk_time(record["talk_time"])
            processed_audio_duration = format_talk_time(AudioSegment.from_file(processed_audio_file).duration_seconds)
            processed_agent_duration = format_talk_time(AudioSegment.from_file(processed_agent_file).duration_seconds)
            processed_client_duration = format_talk_time(AudioSegment.from_file(processed_client_file).duration_seconds)
            call_type = "Outgoing"

            if processed_audio_duration >= "30" and processed_agent_duration >= "30" and processed_client_duration >= "30":
                final_transcription = get_transcriptions(agent_name, client_name, processed_audio_file, processed_agent_file, processed_client_file)
                document = create_document(filename, required_date, total_duration, processed_audio_duration, processed_agent_duration, processed_client_duration, final_transcription, agent_name, client_number, client_name, call_type, processed_audio_file, processed_agent_file, processed_client_file)
                insert_result = collection.insert_one(document)
                print("document_inserted")

shutil.rmtree(vad_resampled_folder)