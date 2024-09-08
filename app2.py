import datetime
import random
import streamlit as st
from langchain_ollama import OllamaLLM
import geocoder

def get_user_location():
    g = geocoder.ip('me')
    if g.ok:
        return g.latlng
    else:
        st.warning("Failed to detect location automatically. Please enter your address manually.")
        return st.text_input("Enter your address:")

def find_nearest_hospitals(user_location):
    hospitals = [
        {"name": "City General Hospital", "address": "123 Main St, City", "distance": "2.5 km"},
        {"name": "Community Health Center", "address": "456 Oak Ave, City", "distance": "3.8 km"},
        {"name": "University Medical Center", "address": "789 College Blvd, City", "distance": "5.2 km"}
    ]
    
    for hospital in hospitals:
        hospital["slots"] = initialize_time_slots()
    
    return hospitals

def initialize_time_slots():
    slots = {}
    current_date = datetime.date.today()
    morning_start = datetime.datetime.combine(current_date, datetime.time(9, 0))
    afternoon_start = datetime.datetime.combine(current_date, datetime.time(14, 0))
    evening_end = datetime.datetime.combine(current_date, datetime.time(21, 0))

    current_time = morning_start
    while current_time < evening_end:
        if current_time.time() < datetime.time(13, 0) or current_time.time() >= datetime.time(14, 0):
            slot_key = current_time.strftime("%H:%M")
            slots[slot_key] = 0
        current_time += datetime.timedelta(minutes=20)
    
    return slots

def display_available_slots(hospital):
    available_slots = [time for time, availability in hospital['slots'].items() if availability == 0]
    return available_slots

def allocate_time_slot(hospital, severity):
    slots = hospital['slots']
    current_time = datetime.datetime.now().time()
    
    if severity == "RED":
        return "IMMEDIATE"
    
    for time, availability in slots.items():
        slot_time = datetime.datetime.strptime(time, "%H:%M").time()
        time_difference = datetime.datetime.combine(datetime.date.today(), slot_time) - datetime.datetime.combine(datetime.date.today(), current_time)
        
        if availability == 0:
            if (severity == "ORANGE" and time_difference.total_seconds() > 0) or \
               ((severity == "YELLOW" or severity == "BLUE") and time_difference.total_seconds() > 3600):
                slots[time] = 1
                return time
    
    return None

def predict_diseases(symptoms):
    model = OllamaLLM(model='llama3.1')
    input_prompt = f"""You are an AI assistant designed to help diagnose potential health issues based on reported symptoms.
     Your goal is to analyze the provided symptoms and suggest possible diagnoses along with severity levels.
     Based on the symptoms: {symptoms}, please follow these steps:
     1. Read through the symptoms carefully and think through potential diagnoses.
     2. Provide your assessment in the following format:
     The most likely diagnosis based on the symptoms is: [DIAGNOSIS]
     The severity level is: [RED/ORANGE/YELLOW/BLUE/GREEN]
     [RECOMMENDED ACTIONS BASED ON SEVERITY LEVEL GUIDELINES PROVIDED BELOW]
     Severity Level Guidelines:
     RED (80-100): Rush to the hospital immediately.
     ORANGE (60-80): Consult a doctor or visit a 'Mohalla Clinic' soon and follow basic remedies until then.
     YELLOW (40-60): Visit a 'Mohalla Clinic' or take an online consultation.
     BLUE (20-40): Mild issue. Suggest home remedies.
     GREEN (0-20): No significant health problem, no medical visit required.
     3. If no diagnosis can be made based on the symptoms, state that clearly."""
    result = model.invoke(input=input_prompt)
    return result

def parse_severity(diagnosis):
    severity_levels = ["RED", "ORANGE", "YELLOW", "BLUE", "GREEN"]
    for level in severity_levels:
        if level in diagnosis:
            return level
    return "UNKNOWN"

def health_chatbot():
    st.title("Health Chatbot")
    
    if 'stage' not in st.session_state:
        st.session_state.stage = 'symptoms'
    
    if 'diagnosis' not in st.session_state:
        st.session_state.diagnosis = None
    
    if 'severity' not in st.session_state:
        st.session_state.severity = None
    
    if 'chosen_hospital' not in st.session_state:
        st.session_state.chosen_hospital = None
    
    if 'allocated_slot' not in st.session_state:
        st.session_state.allocated_slot = None
    
    if st.session_state.stage == 'symptoms':
        symptoms = st.text_area("Please enter your symptoms:")
        if st.button("Analyze Symptoms"):
            with st.spinner("Analyzing symptoms..."):
                st.session_state.diagnosis = predict_diseases(symptoms)
                st.session_state.severity = parse_severity(st.session_state.diagnosis)
            st.session_state.stage = 'diagnosis'
    
    elif st.session_state.stage == 'diagnosis':
        st.write("Based on your symptoms, here is the assessment:")
        st.write(st.session_state.diagnosis)
        
        if st.session_state.severity in ["RED", "ORANGE", "YELLOW", "BLUE"]:
            user_location = get_user_location()
            nearest_hospitals = find_nearest_hospitals(user_location)
            
            st.write("Nearest hospitals:")
            for i, hospital in enumerate(nearest_hospitals, 1):
                st.write(f"{i}. {hospital['name']} - {hospital['address']} (Distance: {hospital['distance']})")
            
            if st.session_state.severity == "RED":
                st.error("EMERGENCY: Please go to the nearest hospital immediately!")
            else:
                hospital_choice = st.selectbox("Choose a hospital:", [hospital['name'] for hospital in nearest_hospitals])
                st.session_state.chosen_hospital = next(hospital for hospital in nearest_hospitals if hospital['name'] == hospital_choice)
                
                if st.button("Allocate Time Slot"):
                    st.session_state.allocated_slot = allocate_time_slot(st.session_state.chosen_hospital, st.session_state.severity)
                    st.session_state.stage = 'slot_allocation'
        
        elif st.session_state.severity == "GREEN":
            st.success("No medical visit is required at this time. Take care!")
            if st.button("Start Over"):
                st.session_state.stage = 'symptoms'
    
    elif st.session_state.stage == 'slot_allocation':
        if st.session_state.allocated_slot:
            st.write(f"You have been allocated a slot at {st.session_state.chosen_hospital['name']} at {st.session_state.allocated_slot}")
            
            if st.button("Change Slot"):
                st.session_state.stage = 'change_slot'
            elif st.button("Confirm Slot"):
                st.success(f"Your appointment is confirmed for {st.session_state.allocated_slot} at {st.session_state.chosen_hospital['name']}")
                st.session_state.stage = 'final_options'
        else:
            st.error("No available slots for today. Please try again tomorrow or contact the hospital directly.")
            if st.button("Start Over"):
                st.session_state.stage = 'symptoms'
    
    elif st.session_state.stage == 'change_slot':
        available_slots = display_available_slots(st.session_state.chosen_hospital)
        new_slot = st.selectbox("Choose a new time slot:", available_slots)
        
        if st.button("Confirm New Slot"):
            st.session_state.chosen_hospital['slots'][st.session_state.allocated_slot] = 0
            st.session_state.chosen_hospital['slots'][new_slot] = 1
            st.session_state.allocated_slot = new_slot
            st.success(f"Your appointment has been rescheduled to {new_slot}")
            st.session_state.stage = 'final_options'
    
    elif st.session_state.stage == 'final_options':
        st.write("What would you like to do next?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Redo Symptom Analysis"):
                st.session_state.stage = 'symptoms'
        with col2:
            if st.button("End Session"):
                st.write("Thank you for using the Health Chatbot. Take care!")
                st.stop()

if __name__ == "__main__":
    health_chatbot()