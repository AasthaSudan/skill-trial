"""Frozen initial SkillTrial PostgreSQL schema baseline.

This revision is generated from the model snapshot present when it was
created. Future schema changes must be added as new Alembic revisions.
"""
from alembic import op

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

STATEMENTS = (
    "CREATE TABLE app_settings (\n\tkey VARCHAR NOT NULL, \n\tvalue JSON NOT NULL, \n\tupdated_by VARCHAR NOT NULL, \n\tupdated FLOAT NOT NULL, \n\tPRIMARY KEY (key)\n);",
    "CREATE TABLE audit (\n\tid VARCHAR NOT NULL, \n\tactor VARCHAR NOT NULL, \n\taction VARCHAR NOT NULL, \n\ttarget VARCHAR NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (id)\n);",
    "CREATE TABLE badge_definitions (\n\tslug VARCHAR NOT NULL, \n\tname VARCHAR NOT NULL, \n\tdescription VARCHAR NOT NULL, \n\ticon VARCHAR NOT NULL, \n\tmetric VARCHAR NOT NULL, \n\tthresholds JSON NOT NULL, \n\tenabled BOOLEAN NOT NULL, \n\tauthor VARCHAR NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tupdated FLOAT NOT NULL, \n\tPRIMARY KEY (slug)\n);",
    "CREATE TABLE challenges (\n\tid VARCHAR NOT NULL, \n\tslug VARCHAR NOT NULL, \n\tversion INTEGER NOT NULL, \n\tskill VARCHAR NOT NULL, \n\ttype VARCHAR NOT NULL, \n\tpool VARCHAR NOT NULL, \n\tfamily VARCHAR NOT NULL, \n\tlevel VARCHAR NOT NULL, \n\tstatus VARCHAR NOT NULL, \n\tauthor VARCHAR NOT NULL, \n\treviewer VARCHAR, \n\tcontent JSON NOT NULL, \n\tvalidation JSON NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (slug, version)\n);",
    "CREATE INDEX ix_challenges_skill ON challenges (skill);",
    "CREATE INDEX ix_challenges_slug ON challenges (slug);",
    "CREATE TABLE jobs (\n\tid VARCHAR NOT NULL, \n\tkind VARCHAR NOT NULL, \n\ttarget VARCHAR NOT NULL, \n\tstatus VARCHAR NOT NULL, \n\ttries INTEGER NOT NULL, \n\tupdated FLOAT NOT NULL, \n\terror VARCHAR, \n\tPRIMARY KEY (id), \n\tUNIQUE (target)\n);",
    "CREATE INDEX ix_jobs_status ON jobs (status);",
    "CREATE TABLE learning_resources (\n\tid VARCHAR NOT NULL, \n\tslug VARCHAR NOT NULL, \n\tversion INTEGER NOT NULL, \n\tskill VARCHAR NOT NULL, \n\tcompetency VARCHAR NOT NULL, \n\ttitle VARCHAR NOT NULL, \n\tbody TEXT NOT NULL, \n\tquestion VARCHAR NOT NULL, \n\toptions JSON NOT NULL, \n\tanswer INTEGER NOT NULL, \n\tstatus VARCHAR NOT NULL, \n\tvalidation JSON NOT NULL, \n\tauthor VARCHAR NOT NULL, \n\treviewer VARCHAR, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (slug, version)\n);",
    "CREATE INDEX ix_learning_resources_competency ON learning_resources (competency);",
    "CREATE INDEX ix_learning_resources_skill ON learning_resources (skill);",
    "CREATE INDEX ix_learning_resources_slug ON learning_resources (slug);",
    "CREATE TABLE users (\n\tid VARCHAR NOT NULL, \n\temail VARCHAR NOT NULL, \n\tpassword TEXT NOT NULL, \n\tname VARCHAR NOT NULL, \n\trole VARCHAR NOT NULL, \n\tstatus VARCHAR NOT NULL, \n\tverified BOOLEAN NOT NULL, \n\tprofile JSON NOT NULL, \n\tpreferences JSON NOT NULL, \n\tfailures INTEGER NOT NULL, \n\tlocked_until FLOAT NOT NULL, \n\tdelete_at FLOAT, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (email)\n);",
    "CREATE TABLE activities (\n\tkey VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tkind VARCHAR NOT NULL, \n\tfacts JSON NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (key), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_activities_user_id ON activities (user_id);",
    "CREATE TABLE attempts (\n\tid VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tskill VARCHAR NOT NULL, \n\tlevel VARCHAR NOT NULL, \n\tmode VARCHAR NOT NULL, \n\tclaim_snapshot JSON NOT NULL, \n\tpolicy JSON NOT NULL, \n\tstatus VARCHAR NOT NULL, \n\tduration INTEGER NOT NULL, \n\tstarted FLOAT, \n\tdeadline FLOAT, \n\tcompleted FLOAT, \n\treason VARCHAR, \n\tresult JSON, \n\treport_hash VARCHAR, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_attempts_user_id ON attempts (user_id);",
    "CREATE TABLE auth_tokens (\n\ttoken VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tkind VARCHAR NOT NULL, \n\texpires FLOAT NOT NULL, \n\tPRIMARY KEY (token), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE TABLE celebrations (\n\tkey VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\ttitle VARCHAR NOT NULL, \n\tmessage VARCHAR NOT NULL, \n\ttier INTEGER NOT NULL, \n\tseen BOOLEAN NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (key), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_celebrations_user_id ON celebrations (user_id);",
    "CREATE TABLE idempotency (\n\tkey VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tdigest VARCHAR NOT NULL, \n\tresponse JSON NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (key), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE TABLE inbox_notifications (\n\tkey VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tkind VARCHAR NOT NULL, \n\ttitle VARCHAR NOT NULL, \n\tmessage VARCHAR NOT NULL, \n\ttarget VARCHAR NOT NULL, \n\tread BOOLEAN NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (key), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_inbox_notifications_read ON inbox_notifications (read);",
    "CREATE INDEX ix_inbox_notifications_user_id ON inbox_notifications (user_id);",
    "CREATE TABLE league_members (\n\tuser_id VARCHAR NOT NULL, \n\talias VARCHAR NOT NULL, \n\tjoined FLOAT NOT NULL, \n\tPRIMARY KEY (user_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tUNIQUE (alias)\n);",
    "CREATE TABLE learning_paths (\n\tid VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tattempt_id VARCHAR NOT NULL, \n\tskill VARCHAR NOT NULL, \n\titems JSON NOT NULL, \n\tarchived BOOLEAN NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tUNIQUE (attempt_id)\n);",
    "CREATE INDEX ix_learning_paths_user_id ON learning_paths (user_id);",
    "CREATE TABLE notification_outbox (\n\tkey VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tkind VARCHAR NOT NULL, \n\tpayload JSON NOT NULL, \n\tstatus VARCHAR NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tdelivered FLOAT, \n\terror VARCHAR, \n\tPRIMARY KEY (key), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_notification_outbox_status ON notification_outbox (status);",
    "CREATE INDEX ix_notification_outbox_user_id ON notification_outbox (user_id);",
    "CREATE TABLE orbit_progress (\n\tkey VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tskill VARCHAR NOT NULL, \n\tpoints INTEGER NOT NULL, \n\tupdated FLOAT NOT NULL, \n\tPRIMARY KEY (key), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_orbit_progress_user_id ON orbit_progress (user_id);",
    "CREATE TABLE quests (\n\tkey VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\ttitle VARCHAR NOT NULL, \n\tkind VARCHAR NOT NULL, \n\ttarget INTEGER NOT NULL, \n\tpoints INTEGER NOT NULL, \n\tstart FLOAT NOT NULL, \n\t\"end\" FLOAT NOT NULL, \n\tclaimed BOOLEAN NOT NULL, \n\tPRIMARY KEY (key), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_quests_user_id ON quests (user_id);",
    "CREATE TABLE report_shares (\n\tid VARCHAR NOT NULL, \n\ttoken_hash VARCHAR NOT NULL, \n\ttoken_hint VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tlabel VARCHAR NOT NULL, \n\toptions JSON NOT NULL, \n\texpires FLOAT NOT NULL, \n\trevoked FLOAT, \n\tcreated FLOAT NOT NULL, \n\tlast_accessed FLOAT, \n\taccess_count INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE UNIQUE INDEX ix_report_shares_token_hash ON report_shares (token_hash);",
    "CREATE INDEX ix_report_shares_user_id ON report_shares (user_id);",
    "CREATE TABLE resumes (\n\tid VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tfilename VARCHAR NOT NULL, \n\tdigest VARCHAR NOT NULL, \n\tstatus VARCHAR NOT NULL, \n\tdetail JSON NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_resumes_user_id ON resumes (user_id);",
    "CREATE TABLE sessions (\n\ttoken VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tcsrf VARCHAR NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tseen FLOAT NOT NULL, \n\tPRIMARY KEY (token), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_sessions_user_id ON sessions (user_id);",
    "CREATE TABLE xp_ledger (\n\tkey VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tpoints INTEGER NOT NULL, \n\tlabel VARCHAR NOT NULL, \n\tsource VARCHAR NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (key), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_xp_ledger_user_id ON xp_ledger (user_id);",
    "CREATE TABLE claims (\n\tid VARCHAR NOT NULL, \n\tuser_id VARCHAR NOT NULL, \n\tresume_id VARCHAR, \n\tskill VARCHAR NOT NULL, \n\tlevel VARCHAR, \n\toriginal_level VARCHAR, \n\tstatus VARCHAR NOT NULL, \n\tselected BOOLEAN NOT NULL, \n\tevidence JSON NOT NULL, \n\tconfidence FLOAT NOT NULL, \n\tsource VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (user_id, skill), \n\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tFOREIGN KEY(resume_id) REFERENCES resumes (id) ON DELETE SET NULL\n);",
    "CREATE INDEX ix_claims_user_id ON claims (user_id);",
    "CREATE TABLE items (\n\tid VARCHAR NOT NULL, \n\tattempt_id VARCHAR NOT NULL, \n\tchallenge_id VARCHAR NOT NULL, \n\tordinal INTEGER NOT NULL, \n\tstatus VARCHAR NOT NULL, \n\tdraft JSON NOT NULL, \n\trevision INTEGER NOT NULL, \n\tsaved FLOAT, \n\tsubmission JSON, \n\tevaluation JSON, \n\trun_count INTEGER NOT NULL, \n\tlast_run FLOAT NOT NULL, \n\thints INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(attempt_id) REFERENCES attempts (id) ON DELETE CASCADE, \n\tFOREIGN KEY(challenge_id) REFERENCES challenges (id)\n);",
    "CREATE INDEX ix_items_attempt_id ON items (attempt_id);",
    "CREATE TABLE report_share_items (\n\tid VARCHAR NOT NULL, \n\tshare_id VARCHAR NOT NULL, \n\tattempt_id VARCHAR NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (share_id, attempt_id), \n\tFOREIGN KEY(share_id) REFERENCES report_shares (id) ON DELETE CASCADE, \n\tFOREIGN KEY(attempt_id) REFERENCES attempts (id) ON DELETE CASCADE\n);",
    "CREATE INDEX ix_report_share_items_attempt_id ON report_share_items (attempt_id);",
    "CREATE INDEX ix_report_share_items_share_id ON report_share_items (share_id);",
    "CREATE TABLE share_access_logs (\n\tid VARCHAR NOT NULL, \n\tshare_id VARCHAR, \n\toutcome VARCHAR NOT NULL, \n\tcreated FLOAT NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(share_id) REFERENCES report_shares (id) ON DELETE SET NULL\n);",
    "CREATE INDEX ix_share_access_logs_share_id ON share_access_logs (share_id);",
)


def upgrade():
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade():
    raise RuntimeError('The initial SkillTrial schema contains candidate data; restore a verified backup instead of dropping it.')
