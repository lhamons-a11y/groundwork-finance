-- schema_version: 20260725-byb
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
	debt_type VARCHAR(20), 
	end_date DATE, 
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
	PRIMARY KEY (id), 
	FOREIGN KEY(debt_account_id) REFERENCES debt_accounts (id), 
	FOREIGN KEY(category_id) REFERENCES categories (id)
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
CREATE TABLE pdf_extract_cache (
	source_hash VARCHAR(64) NOT NULL, 
	issuer VARCHAR(40), 
	extracted_json TEXT NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (source_hash)
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
CREATE INDEX ix_ctl_checking_txn ON checking_transaction_links (checking_transaction_id);
CREATE INDEX ix_ctl_debt_entry ON checking_transaction_links (debt_ledger_entry_id);
CREATE INDEX ix_dle_account_date ON debt_ledger_entries (debt_account_id, entry_date);
CREATE INDEX ix_dle_entry_type ON debt_ledger_entries (entry_type);
CREATE INDEX ix_dle_recurring ON debt_ledger_entries (linked_recurring_payment_id);
CREATE INDEX ix_dle_source_type ON debt_ledger_entries (source_type);
CREATE INDEX ix_hist_category_created ON historian_entries (event_category, created_at);
CREATE INDEX ix_hist_category_debt ON historian_entries (event_category, debt_account_id);
CREATE INDEX ix_hist_debt_created ON historian_entries (debt_account_id, created_at);
CREATE INDEX ix_rdp_account_active ON recurring_debt_payments (debt_account_id, is_active);
CREATE INDEX ix_rdp_schedule_active ON recurring_debt_payments (scheduled_date_of_month, is_active);
CREATE INDEX ix_trip_history_dates ON trip_history (start_date, end_date);
CREATE INDEX ix_trip_history_region ON trip_history (region);
CREATE INDEX ix_txn_account_date ON transactions (account_id, date);
CREATE INDEX ix_txn_account_import ON transactions (account_id, import_id);
CREATE INDEX ix_txn_category ON transactions (category_id);
