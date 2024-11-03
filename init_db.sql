# run the following
# 1. login to psql shell
# 2. run the following command:
#       docker exec -it postgres psql -U admin -d jitc_gen_ai_db

CREATE TABLE IF NOT EXISTS interactions (
    id SERIAL PRIMARY KEY,
    user_query TEXT NOT NULL,
    model_response TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);