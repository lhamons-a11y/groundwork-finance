-- schema_version: 20261009-municipal-utilities
CREATE TABLE accounts (
	id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	type VARCHAR(40), 
	institution VARCHAR(120), 
	currency VARCHAR(3), 
	balance FLOAT, 
	sort_order INTEGER, 
	is_active BOOLEAN, 
	created_at DATETIME, 
	minimum_balance FLOAT, 
	portal_url VARCHAR(2048), 
	PRIMARY KEY (id)
);
CREATE TABLE achievements (
	id INTEGER NOT NULL, 
	achievement_id VARCHAR(60) NOT NULL, 
	section VARCHAR(40), 
	earned_at DATETIME, 
	notified BOOLEAN, 
	extra_data TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (achievement_id)
);
CREATE TABLE app_settings (
	id INTEGER NOT NULL, 
	"key" VARCHAR(120) NOT NULL, 
	value TEXT, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE ("key")
);
CREATE TABLE artefacts (
	id INTEGER NOT NULL, 
	held BOOLEAN NOT NULL, 
	content_hash VARCHAR(64), 
	as_of VARCHAR(10), 
	encountered_at DATETIME NOT NULL, 
	asserted_by_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asserted_by_id) REFERENCES utterances (id)
);
CREATE TABLE budget_items (
	id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	category VARCHAR(80), 
	amount FLOAT, 
	type VARCHAR(10), 
	sort_order INTEGER, 
	is_active BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE budget_months (
	id INTEGER NOT NULL, 
	plan_id INTEGER NOT NULL, 
	month_key VARCHAR(7) NOT NULL, 
	targets TEXT, 
	actuals TEXT, 
	is_complete BOOLEAN, 
	is_over BOOLEAN, 
	saved_amount FLOAT, 
	coach_note TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(plan_id) REFERENCES budget_plans (id)
);
CREATE TABLE budget_plans (
	id INTEGER NOT NULL, 
	name VARCHAR(120), 
	goal_amount FLOAT, 
	goal_months INTEGER, 
	start_month VARCHAR(7), 
	total_saved FLOAT, 
	streak_count INTEGER, 
	is_active BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE byb_items (
	id INTEGER NOT NULL, 
	item_type VARCHAR(40), 
	name VARCHAR(200), 
	category VARCHAR(80), 
	monthly_cost FLOAT, 
	replacing_name VARCHAR(200), 
	replacing_amount FLOAT, 
	replacing_id INTEGER, 
	days_impact FLOAT, 
	decision VARCHAR(20), 
	dti_before FLOAT, 
	dti_after FLOAT, 
	payoff_impact FLOAT, 
	whats_left_before FLOAT, 
	whats_left_after FLOAT, 
	actual_cost FLOAT, 
	decided_at DATETIME, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE categories (
	id INTEGER NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	type VARCHAR(20), 
	color VARCHAR(10), 
	icon VARCHAR(20), 
	parent_id INTEGER, 
	sort_order INTEGER, 
	is_system BOOLEAN, 
	is_optional BOOLEAN, 
	is_enabled BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	FOREIGN KEY(parent_id) REFERENCES categories (id)
);
CREATE TABLE checking_transaction_links (
	id INTEGER NOT NULL, 
	checking_transaction_id INTEGER NOT NULL, 
	debt_ledger_entry_id INTEGER NOT NULL, 
	link_indicator VARCHAR(20) NOT NULL, 
	created_at DATETIME, 
	user_confirmed_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_checking_debt_link UNIQUE (checking_transaction_id, debt_ledger_entry_id), 
	FOREIGN KEY(checking_transaction_id) REFERENCES transactions (id), 
	FOREIGN KEY(debt_ledger_entry_id) REFERENCES debt_ledger_entries (id)
);
CREATE TABLE debt_accounts (
	id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	begin_balance FLOAT, 
	current_balance FLOAT, 
	start_date DATE, 
	interest_rate FLOAT, 
	minimum_payment FLOAT, 
	due_day INTEGER, 
	is_active BOOLEAN, 
	paid_off_at DATETIME, 
	sort_order INTEGER, 
	created_at DATETIME, 
	linked_account_id INTEGER, 
	credit_limit FLOAT, 
	interest_rate_source VARCHAR(12), 
	minimum_payment_source VARCHAR(12), 
	debt_type VARCHAR(20), 
	end_date DATE, 
	portal_url VARCHAR(2048), 
	PRIMARY KEY (id), 
	FOREIGN KEY(linked_account_id) REFERENCES accounts (id)
);
CREATE TABLE debt_balance_history (
	id INTEGER NOT NULL, 
	debt_id INTEGER NOT NULL, 
	month VARCHAR(7) NOT NULL, 
	balance FLOAT NOT NULL, 
	payment FLOAT NOT NULL, 
	min_payment FLOAT NOT NULL, 
	apr FLOAT, 
	interest_charged FLOAT, 
	statement_period_end VARCHAR(10), 
	saved_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(debt_id) REFERENCES debt_accounts (id)
);
CREATE TABLE debt_ledger_entries (
	id INTEGER NOT NULL, 
	debt_account_id INTEGER NOT NULL, 
	entry_type VARCHAR(10) NOT NULL, 
	amount FLOAT NOT NULL, 
	entry_date DATE NOT NULL, 
	description VARCHAR(255), 
	category VARCHAR(80), 
	merchant VARCHAR(120), 
	linked_checking_transaction_id INTEGER, 
	source_type VARCHAR(10) NOT NULL, 
	linked_recurring_payment_id INTEGER, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(debt_account_id) REFERENCES debt_accounts (id), 
	FOREIGN KEY(linked_checking_transaction_id) REFERENCES transactions (id), 
	FOREIGN KEY(linked_recurring_payment_id) REFERENCES recurring_debt_payments (id)
);
CREATE TABLE evidence (
	id INTEGER NOT NULL, 
	proposition_id INTEGER NOT NULL, 
	utterance_id INTEGER, 
	reading_id INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(proposition_id) REFERENCES propositions (id), 
	FOREIGN KEY(utterance_id) REFERENCES utterances (id), 
	FOREIGN KEY(reading_id) REFERENCES readings (id)
);
CREATE TABLE expense_determinations (
	id INTEGER NOT NULL, 
	expense_id INTEGER NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	amount FLOAT NOT NULL, 
	evidence VARCHAR(80), 
	rule_version VARCHAR(24), 
	effective_seq FLOAT NOT NULL, 
	recorded_seq INTEGER NOT NULL, 
	supersedes_id INTEGER, 
	recorded_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(expense_id) REFERENCES healthcare_expenses (id), 
	FOREIGN KEY(supersedes_id) REFERENCES expense_determinations (id)
);
CREATE TABLE expense_funding_allocations (
	id INTEGER NOT NULL, 
	expense_id INTEGER NOT NULL, 
	funder VARCHAR(40) NOT NULL, 
	amount FLOAT NOT NULL, 
	mode VARCHAR(24) NOT NULL, 
	source VARCHAR(24), 
	cleared BOOLEAN, 
	attached BOOLEAN, 
	user_confirmed BOOLEAN, 
	duplicate_of VARCHAR(40), 
	occurred_on VARCHAR(10), 
	effective_seq FLOAT NOT NULL, 
	recorded_seq INTEGER NOT NULL, 
	supersedes_id INTEGER, 
	recorded_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(expense_id) REFERENCES healthcare_expenses (id), 
	FOREIGN KEY(supersedes_id) REFERENCES expense_funding_allocations (id)
);
CREATE TABLE expense_merge_links (
	id INTEGER NOT NULL, 
	merged_into_id INTEGER NOT NULL, 
	merged_from_id INTEGER NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(merged_into_id) REFERENCES healthcare_expenses (id), 
	FOREIGN KEY(merged_from_id) REFERENCES healthcare_expenses (id)
);
CREATE TABLE expense_obligation_versions (
	id INTEGER NOT NULL, 
	expense_id INTEGER NOT NULL, 
	amount FLOAT NOT NULL, 
	effective_seq FLOAT NOT NULL, 
	recorded_seq INTEGER NOT NULL, 
	supersedes_id INTEGER, 
	recorded_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(expense_id) REFERENCES healthcare_expenses (id), 
	FOREIGN KEY(supersedes_id) REFERENCES expense_obligation_versions (id)
);
CREATE TABLE expense_refunds (
	id INTEGER NOT NULL, 
	expense_id INTEGER NOT NULL, 
	amount FLOAT NOT NULL, 
	to_funder VARCHAR(40), 
	occurred_on VARCHAR(10), 
	effective_seq FLOAT NOT NULL, 
	recorded_seq INTEGER NOT NULL, 
	recorded_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(expense_id) REFERENCES healthcare_expenses (id)
);
CREATE TABLE expenses (
	id INTEGER NOT NULL, 
	minted_by_id INTEGER NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(minted_by_id) REFERENCES utterances (id)
);
CREATE TABLE flight_price_cache (
	cache_key VARCHAR(64) NOT NULL, 
	origin VARCHAR(10) NOT NULL, 
	destination VARCHAR(10) NOT NULL, 
	outbound_date VARCHAR(10) NOT NULL, 
	return_date VARCHAR(10), 
	travelers INTEGER, 
	price_total FLOAT, 
	airline VARCHAR(120), 
	raw_json TEXT, 
	fetched_at DATETIME, 
	PRIMARY KEY (cache_key)
);
CREATE TABLE health_plan_operations (
	id INTEGER NOT NULL, 
	plan_id INTEGER NOT NULL, 
	kind VARCHAR(16) NOT NULL, 
	seq INTEGER NOT NULL, 
	recorded_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(plan_id) REFERENCES health_plans (id)
);
CREATE TABLE health_plan_term_versions (
	id INTEGER NOT NULL, 
	plan_id INTEGER NOT NULL, 
	deductible FLOAT, 
	oop_max FLOAT, 
	previous_deductible FLOAT, 
	previous_oop_max FLOAT, 
	reason VARCHAR(200), 
	source VARCHAR(40), 
	seq INTEGER NOT NULL, 
	recorded_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(plan_id) REFERENCES health_plans (id)
);
CREATE TABLE health_plans (
	id INTEGER NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	effective_from VARCHAR(10) NOT NULL, 
	effective_to VARCHAR(10), 
	seq INTEGER NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE healthcare_expenses (
	id INTEGER NOT NULL, 
	incurred_on VARCHAR(10) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE historian_entries (
	id INTEGER NOT NULL, 
	event_category VARCHAR(40) NOT NULL, 
	debt_account_id INTEGER, 
	category_id INTEGER, 
	expected_value FLOAT, 
	actual_value FLOAT, 
	variance_pct FLOAT, 
	variance_amount FLOAT, 
	context_json TEXT, 
	created_at DATETIME, 
	healthcare_expense_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(debt_account_id) REFERENCES debt_accounts (id), 
	FOREIGN KEY(category_id) REFERENCES categories (id), 
	FOREIGN KEY(healthcare_expense_id) REFERENCES healthcare_expenses (id)
);
CREATE TABLE household_facts (
	id INTEGER NOT NULL, 
	"key" VARCHAR(40) NOT NULL, 
	value VARCHAR(80), 
	answered_at DATETIME, 
	source VARCHAR(20) NOT NULL, 
	recorded_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE investment_lots (
	id INTEGER NOT NULL, 
	account_id INTEGER, 
	source_transaction_id INTEGER, 
	ticker VARCHAR(20) NOT NULL, 
	security_type VARCHAR(20), 
	shares_original FLOAT, 
	shares_remaining FLOAT, 
	cost_basis_per_share FLOAT, 
	purchase_date DATE NOT NULL, 
	is_closed BOOLEAN, 
	closed_date DATE, 
	sell_price_per_share FLOAT, 
	realized_gain FLOAT, 
	realized_gain_pct FLOAT, 
	holding_period_days INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id), 
	FOREIGN KEY(source_transaction_id) REFERENCES investment_transactions (id)
);
CREATE TABLE investment_transactions (
	id INTEGER NOT NULL, 
	account_id INTEGER, 
	date DATE NOT NULL, 
	ticker VARCHAR(20) NOT NULL, 
	type VARCHAR(20) NOT NULL, 
	security_type VARCHAR(20), 
	shares FLOAT, 
	price_per_share FLOAT, 
	total_amount FLOAT, 
	fees FLOAT, 
	note TEXT, 
	meta TEXT, 
	import_source VARCHAR(20), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id)
);
CREATE TABLE net_worth_snapshots (
	id INTEGER NOT NULL, 
	snapshot_date VARCHAR(10) NOT NULL, 
	net_worth FLOAT, 
	assets FLOAT, 
	liabilities FLOAT, 
	notes TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE obligations (
	id INTEGER NOT NULL, 
	minted_by_id INTEGER NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(minted_by_id) REFERENCES utterances (id)
);
CREATE TABLE parties (
	id INTEGER NOT NULL, 
	person_id INTEGER, 
	minted_by_id INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (person_id), 
	FOREIGN KEY(person_id) REFERENCES people (id), 
	CONSTRAINT fk_party_minted_by FOREIGN KEY(minted_by_id) REFERENCES utterances (id)
);
CREATE TABLE payments (
	id INTEGER NOT NULL, 
	minted_by_id INTEGER NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(minted_by_id) REFERENCES utterances (id)
);
CREATE TABLE pdf_extract_cache (
	source_hash VARCHAR(64) NOT NULL, 
	issuer VARCHAR(40), 
	extracted_json TEXT NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (source_hash)
);
CREATE TABLE people (
	id INTEGER NOT NULL, 
	display_name VARCHAR(80) NOT NULL, 
	active BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE person_aliases (
	id INTEGER NOT NULL, 
	person_id INTEGER NOT NULL, 
	alias VARCHAR(120) NOT NULL, 
	source VARCHAR(40), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(person_id) REFERENCES people (id)
);
CREATE TABLE person_assignments (
	id INTEGER NOT NULL, 
	expense_id INTEGER NOT NULL, 
	person_id INTEGER NOT NULL, 
	mode VARCHAR(16) NOT NULL, 
	seq INTEGER NOT NULL, 
	reason VARCHAR(200), 
	source VARCHAR(40), 
	recorded_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(expense_id) REFERENCES healthcare_expenses (id), 
	FOREIGN KEY(person_id) REFERENCES people (id)
);
CREATE TABLE person_enrolments (
	id INTEGER NOT NULL, 
	person_id INTEGER NOT NULL, 
	plan_id INTEGER NOT NULL, 
	effective_on VARCHAR(10), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(person_id) REFERENCES people (id), 
	FOREIGN KEY(plan_id) REFERENCES health_plans (id)
);
CREATE TABLE plans (
	id INTEGER NOT NULL, 
	minted_by_id INTEGER NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(minted_by_id) REFERENCES utterances (id)
);
CREATE TABLE price_cache (
	ticker VARCHAR(20) NOT NULL, 
	price FLOAT, 
	previous_close FLOAT, 
	day_change FLOAT, 
	day_change_pct FLOAT, 
	company_name VARCHAR(120), 
	currency VARCHAR(3), 
	market_state VARCHAR(20), 
	last_updated DATETIME, 
	is_manual BOOLEAN, 
	source VARCHAR(20), 
	PRIMARY KEY (ticker)
);
CREATE TABLE propositions (
	id INTEGER NOT NULL, 
	kind VARCHAR(48) NOT NULL, 
	subject_state VARCHAR(32) NOT NULL, 
	subject_party_id INTEGER, 
	subject_utterance_id INTEGER, 
	subject_artefact_id INTEGER, 
	subject_obligation_id INTEGER, 
	subject_payment_id INTEGER, 
	subject_expense_id INTEGER, 
	subject_plan_id INTEGER, 
	subject_proposition_id INTEGER, 
	object_proposition_id INTEGER, 
	object_state VARCHAR(32) NOT NULL, 
	object_party_id INTEGER, 
	object_utterance_id INTEGER, 
	object_artefact_id INTEGER, 
	object_obligation_id INTEGER, 
	object_payment_id INTEGER, 
	object_expense_id INTEGER, 
	object_plan_id INTEGER, 
	content TEXT, 
	as_of VARCHAR(10), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(subject_party_id) REFERENCES parties (id), 
	FOREIGN KEY(subject_utterance_id) REFERENCES utterances (id), 
	FOREIGN KEY(subject_artefact_id) REFERENCES artefacts (id), 
	FOREIGN KEY(subject_obligation_id) REFERENCES obligations (id), 
	FOREIGN KEY(subject_payment_id) REFERENCES payments (id), 
	FOREIGN KEY(subject_expense_id) REFERENCES expenses (id), 
	FOREIGN KEY(subject_plan_id) REFERENCES plans (id), 
	FOREIGN KEY(subject_proposition_id) REFERENCES propositions (id), 
	FOREIGN KEY(object_proposition_id) REFERENCES propositions (id), 
	FOREIGN KEY(object_party_id) REFERENCES parties (id), 
	FOREIGN KEY(object_utterance_id) REFERENCES utterances (id), 
	FOREIGN KEY(object_artefact_id) REFERENCES artefacts (id), 
	FOREIGN KEY(object_obligation_id) REFERENCES obligations (id), 
	FOREIGN KEY(object_payment_id) REFERENCES payments (id), 
	FOREIGN KEY(object_expense_id) REFERENCES expenses (id), 
	FOREIGN KEY(object_plan_id) REFERENCES plans (id)
);
CREATE TABLE readings (
	id INTEGER NOT NULL, 
	artefact_id INTEGER NOT NULL, 
	read_at DATETIME NOT NULL, 
	reader_party_id INTEGER, 
	reader_process VARCHAR(80), 
	PRIMARY KEY (id), 
	FOREIGN KEY(artefact_id) REFERENCES artefacts (id), 
	FOREIGN KEY(reader_party_id) REFERENCES parties (id)
);
CREATE TABLE recurring_debt_payments (
	id INTEGER NOT NULL, 
	debt_account_id INTEGER NOT NULL, 
	scheduled_date_of_month INTEGER, 
	amount FLOAT NOT NULL, 
	frequency VARCHAR(10), 
	is_active BOOLEAN, 
	is_auto_confirm BOOLEAN, 
	created_at DATETIME, 
	last_confirmed_at DATETIME, 
	last_executed_at DATETIME, 
	created_from_transaction_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(debt_account_id) REFERENCES debt_accounts (id), 
	FOREIGN KEY(created_from_transaction_id) REFERENCES transactions (id)
);
CREATE TABLE reserve_allocations (
	id INTEGER NOT NULL, 
	amount FLOAT NOT NULL, 
	as_of VARCHAR(10), 
	reason VARCHAR(200), 
	source VARCHAR(40), 
	seq INTEGER NOT NULL, 
	recorded_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE reserve_targets (
	id INTEGER NOT NULL, 
	basis VARCHAR(20), 
	amount FLOAT, 
	kind VARCHAR(20) NOT NULL, 
	source VARCHAR(40), 
	reason VARCHAR(200), 
	cleared BOOLEAN, 
	seq INTEGER NOT NULL, 
	recorded_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE sinking_funds (
	id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	target_amount FLOAT, 
	current_amount FLOAT, 
	deadline VARCHAR(10), 
	monthly_contribution FLOAT, 
	note TEXT, 
	is_active BOOLEAN, 
	last_contributed_month VARCHAR(7), 
	created_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE tax_rule_versions (
	id INTEGER NOT NULL, 
	version VARCHAR(24) NOT NULL, 
	effective_seq FLOAT NOT NULL, 
	recorded_seq INTEGER NOT NULL, 
	recorded_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE transactions (
	id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	description VARCHAR(255), 
	amount FLOAT NOT NULL, 
	type VARCHAR(10), 
	category_id INTEGER, 
	account_id INTEGER, 
	ticker VARCHAR(20), 
	cleared BOOLEAN, 
	memo TEXT, 
	import_id VARCHAR(64), 
	created_at DATETIME, 
	merchant VARCHAR(120), 
	posted_date DATE, 
	running_balance FLOAT, 
	mcc VARCHAR(4), 
	card_last4 VARCHAR(4), 
	source VARCHAR(10), 
	check_number VARCHAR(20), 
	PRIMARY KEY (id), 
	FOREIGN KEY(category_id) REFERENCES categories (id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id)
);
CREATE TABLE trip_bookings (
	id INTEGER NOT NULL, 
	trip_label VARCHAR(160), 
	airline VARCHAR(80) NOT NULL, 
	amount FLOAT NOT NULL, 
	booked_on DATE NOT NULL, 
	paid_with_kind VARCHAR(10) NOT NULL, 
	debt_account_id INTEGER, 
	account_id INTEGER, 
	confirmation VARCHAR(40), 
	status VARCHAR(12) NOT NULL, 
	refund_expected BOOLEAN, 
	matched_transaction_id INTEGER, 
	matched_debt_entry_id INTEGER, 
	charged_amount FLOAT, 
	refund_transaction_id INTEGER, 
	refund_debt_entry_id INTEGER, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(debt_account_id) REFERENCES debt_accounts (id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id), 
	FOREIGN KEY(matched_transaction_id) REFERENCES transactions (id), 
	FOREIGN KEY(matched_debt_entry_id) REFERENCES debt_ledger_entries (id), 
	FOREIGN KEY(refund_transaction_id) REFERENCES transactions (id), 
	FOREIGN KEY(refund_debt_entry_id) REFERENCES debt_ledger_entries (id)
);
CREATE TABLE trip_history (
	id INTEGER NOT NULL, 
	trip_label VARCHAR(120), 
	region VARCHAR(80), 
	start_date DATE, 
	end_date DATE, 
	estimated_total FLOAT, 
	actual_total FLOAT, 
	estimated_by_category TEXT, 
	actual_by_category TEXT, 
	learned_basis_json TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE utterances (
	id INTEGER NOT NULL, 
	origin_party_id INTEGER NOT NULL, 
	asserted_at VARCHAR(19), 
	recorded_at DATETIME NOT NULL, 
	content TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(origin_party_id) REFERENCES parties (id)
);
CREATE TABLE willingness_declarations (
	id INTEGER NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	stance VARCHAR(10) NOT NULL, 
	answer_kind VARCHAR(10) NOT NULL, 
	answer_text TEXT, 
	said_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_artefact_hash ON artefacts (content_hash);
CREATE INDEX ix_ctl_checking_txn ON checking_transaction_links (checking_transaction_id);
CREATE INDEX ix_ctl_debt_entry ON checking_transaction_links (debt_ledger_entry_id);
CREATE INDEX ix_dle_account_date ON debt_ledger_entries (debt_account_id, entry_date);
CREATE INDEX ix_dle_entry_type ON debt_ledger_entries (entry_type);
CREATE INDEX ix_dle_recurring ON debt_ledger_entries (linked_recurring_payment_id);
CREATE INDEX ix_dle_source_type ON debt_ledger_entries (source_type);
CREATE INDEX ix_edet_expense ON expense_determinations (expense_id);
CREATE INDEX ix_efa_expense ON expense_funding_allocations (expense_id);
CREATE INDEX ix_eov_expense ON expense_obligation_versions (expense_id);
CREATE INDEX ix_eref_expense ON expense_refunds (expense_id);
CREATE INDEX ix_evidence_proposition ON evidence (proposition_id);
CREATE INDEX ix_evidence_reading ON evidence (reading_id);
CREATE INDEX ix_evidence_utterance ON evidence (utterance_id);
CREATE INDEX ix_hist_category_created ON historian_entries (event_category, created_at);
CREATE INDEX ix_hist_category_debt ON historian_entries (event_category, debt_account_id);
CREATE INDEX ix_hist_debt_created ON historian_entries (debt_account_id, created_at);
CREATE INDEX ix_household_facts_key ON household_facts ("key");
CREATE INDEX ix_person_alias ON person_aliases (alias);
CREATE INDEX ix_person_assign_expense ON person_assignments (expense_id);
CREATE INDEX ix_prop_kind ON propositions (kind);
CREATE INDEX ix_prop_object_expense ON propositions (object_expense_id);
CREATE INDEX ix_prop_object_obligation ON propositions (object_obligation_id);
CREATE INDEX ix_prop_object_payment ON propositions (object_payment_id);
CREATE INDEX ix_prop_object_plan ON propositions (object_plan_id);
CREATE INDEX ix_prop_object_proposition ON propositions (object_proposition_id);
CREATE INDEX ix_prop_subject_artefact ON propositions (subject_artefact_id);
CREATE INDEX ix_prop_subject_expense ON propositions (subject_expense_id);
CREATE INDEX ix_prop_subject_obligation ON propositions (subject_obligation_id);
CREATE INDEX ix_prop_subject_party ON propositions (subject_party_id);
CREATE INDEX ix_prop_subject_payment ON propositions (subject_payment_id);
CREATE INDEX ix_prop_subject_plan ON propositions (subject_plan_id);
CREATE INDEX ix_prop_subject_proposition ON propositions (subject_proposition_id);
CREATE INDEX ix_prop_subject_utterance ON propositions (subject_utterance_id);
CREATE INDEX ix_rdp_account_active ON recurring_debt_payments (debt_account_id, is_active);
CREATE INDEX ix_rdp_schedule_active ON recurring_debt_payments (scheduled_date_of_month, is_active);
CREATE INDEX ix_reading_artefact ON readings (artefact_id);
CREATE INDEX ix_trip_history_dates ON trip_history (start_date, end_date);
CREATE INDEX ix_trip_history_region ON trip_history (region);
CREATE INDEX ix_txn_account_date ON transactions (account_id, date);
CREATE INDEX ix_txn_account_import ON transactions (account_id, import_id);
CREATE INDEX ix_txn_category ON transactions (category_id);
