Generate the baseline from the models, then apply:
    alembic revision --autogenerate -m "baseline"
    alembic upgrade head
Hypertable, compression, retention and the audit trigger are created by `app.db.session.HARDENING`; keep them out of autogenerate.
