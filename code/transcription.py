import whisper
from fuzzywuzzy import fuzz

def transcribe_whisper(audio):
    model = whisper.load_model("medium.en")
    result = model.transcribe(audio)
    return result

def word_replace(transcription):
    word_dict = {"CureMD": ["CARAMD", "Caramd", "caramd", "CARE MD", "Care md", "care md", "CAREER MD", "Career md", "career md", "CAREMD", "Caremd", "caremd", "CMD", "Cmd",
                            "cmd", "CRMD", "Crmd", "crmd", "CURE MEDI", "Cure medi", "cure medi","CURAMD", "Curamd", "curamd", "KAREM", "Karem", "karem", "KAREMD", "Karemd",
                            "karemd", "KARM Z", "Karm z", "karm z", "KEREMD", "Keremd", "keremd", "KERIMD", "Kerimd", "kerimd", "KERM D", "Kerm d", "kerm d", "KMD", "Kmd",
                            "kmd", "KOMD", "Komd", "komd", "KRMERY", "Krmery", "krmery", "KRMD", "Krmd", "krmd", "KEMBRY", "Kembry", "kembry", "QMD", "Qmd", "qmd", "QM-G",
                            "Qm-g", "qm-g", "QMV", "Qmv", "qmv", "Q&MD", "Q&md", "q&md", "QRMD", "Qrmd", "qrmd","CAREMEY", "Caremey", "caremey", "QM&D", "Qm&d", "qm&d",
                            "KERMADEE", "Kermadee", "kermadee", "KEREMLY", "Keremly", "keremly", "QM-D", "Qm-d", "qm-d"]}

    for i in range(len(transcription)):
        for key, values in word_dict.items():
            for value in values:
                if value in transcription:
                    transcription = transcription.replace(value, key)
    return transcription

def __get_transcriptions_lists(transcribed_audio, transcribed_audio_agent, transcribed_audio_client):
    audio_transcription = word_replace([[line['text'], line['start'], line['end']] for line in transcribed_audio["segments"]])
    agent_transcription = word_replace([[line['text'], line['start'], line['end']]  for line in transcribed_audio_agent["segments"]])
    client_transcription = word_replace([[line['text'], line['start'], line['end']]  for line in transcribed_audio_client["segments"]])
    return audio_transcription, agent_transcription, client_transcription

def find_best_match(line, sentences):
    if not sentences:
        return 0
    return max([fuzz.ratio(line, sentence[0]) for sentence in sentences])

# Function to format time in MM:SS
def format_time(seconds):
    return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"

# Function to merge consecutive segments based on the speaker
def merge_consecutive_segments(segment_list):
    if not segment_list:
        return []
    
    merged_segments = []
    current_segment = segment_list[0]

    for segment in segment_list[1:]:
        if segment['Speaker'] == current_segment['Speaker']:
            current_segment['Text'] += ' ' + segment['Text']
            current_segment['End'] = segment['End']
        else:
            current_segment['Time'] = f"[{format_time(current_segment['Start'])} - {format_time(current_segment['End'])}]"
            merged_segments.append(current_segment)
            current_segment = segment
    
    # Append the last segment
    current_segment['Time'] = f"[{format_time(current_segment['Start'])} - {format_time(current_segment['End'])}]"
    merged_segments.append(current_segment)
    
    return merged_segments

# Function to classify speaker and create the dialogue
def generate_transcriptions(audio_transcription, agent_transcription, client_transcription):
    transcriptions = []
    
    for line in audio_transcription:
        agent_score = find_best_match(line[0], agent_transcription)
        client_score = find_best_match(line[0], client_transcription)
        
        speaker = "Agent" if agent_score > client_score else "Client"
        
        transcriptions.append({
            "Speaker": speaker,
            "Text": line[0],
            "Start": round(line[1], 1),
            "End": round(line[2], 1)
        })
    return merge_consecutive_segments(transcriptions)

def format_dialogue(transcriptions, agent_name, client_name):
    dialogue = []
    for segment in transcriptions:
        speaker = agent_name if segment['Speaker'] == "Agent" else client_name
        dialogue.append(f"{speaker}: {segment['Text']} {segment['Time']}")
    
    return "\n".join(dialogue)

def get_transcriptions(agent_name, client_name, audio, agent_audio, client_audio):
    transcribed_audio = transcribe_whisper(audio)
    transcribed_audio_agent = transcribe_whisper(agent_audio)
    transcribed_audio_client = transcribe_whisper(client_audio)
    audio_transcription, agent_transcription, client_transcription = __get_transcriptions_lists(transcribed_audio, transcribed_audio_agent, transcribed_audio_client)

    if not audio_transcription or not agent_transcription or not client_transcription:
        print("Error: One or more transcription inputs are empty.")
        return None
    
    if audio_transcription is None or agent_transcription is None or client_transcription is None:
        print("Error: One or more transcription inputs are invalid.")
        exit(1)

    transcriptions = generate_transcriptions(audio_transcription, agent_transcription, client_transcription)
    formatted_dialogue = format_dialogue(transcriptions, agent_name, client_name)
    final_transcription = word_replace(formatted_dialogue)
    return (final_transcription)