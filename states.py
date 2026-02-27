from aiogram.fsm.state import State, StatesGroup


class PersonalStates(StatesGroup):
    full_name = State()
    birth_date = State()
    region = State()
    district = State()
    mahalla = State()
    work_start_date = State()


class ProfessionalStates(StatesGroup):
    obyektivka = State()
    lang_cert_choice = State()
    lang_cert_doc = State()
    namunali = State()
    namunali_doc = State()
    top100 = State()
    top100_doc = State()
    initiative = State()
    initiative_doc = State()
    additional_achievements = State()
    additional_achievements_doc = State()
    state_award = State()
    state_award_doc = State()
    argos = State()
    argos_doc = State()
    social_networks = State()
    social_telegram = State()
    social_telegram_input = State()
    social_facebook = State()
    social_facebook_input = State()
    social_instagram = State()
    social_instagram_input = State()
    mega_projects = State()
    mega_projects_count = State()


class EssayStates(StatesGroup):
    upload = State()


class ConfirmStates(StatesGroup):
    confirm = State()
    edit_choice = State()


class AdminStates(StatesGroup):
    waiting_password = State()
    main_menu = State()
    
    # Filter/Search states
    search_candidate = State()
    
    # Score states
    score_experience = State()
    score_results = State()
    score_motivation = State()
    score_essay = State()
    score_comment = State()
    
    # Interview states
    interview_date = State()
    interview_time = State()
    interview_location = State()
    interview_note = State()
    interview_status = State()
    
    # System states
    change_min_score = State()
    create_admin = State()

class AdminManagementStates(StatesGroup):
    menu = State()
    add_id = State()
    add_username = State()
    add_role = State()
    add_password = State()
    delete_id = State()
