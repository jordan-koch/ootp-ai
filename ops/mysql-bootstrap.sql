-- ootp-ai — MySQL bootstrap
--
-- Run ONCE as root after installing MySQL, before filling in .env:
--     mysql -u root -p < ops/mysql-bootstrap.sql
--
-- Replace CHANGE_ME below with a password you generate. It belongs in .env as
-- MYSQL_PASSWORD and nowhere else. This file is TRACKED and this repo is PUBLIC
-- (ADR 0006) — a real credential committed here is permanent.
--
-- Do NOT create the application user through the MySQL configurator's "user
-- accounts" step instead of this script. Its "DB Admin" role grants SUPER,
-- FILE, SHUTDOWN, RELOAD and CREATE USER on *.* WITH GRANT OPTION — a near-root
-- account for a pipeline that only ever touches three databases.

-- ── Databases ───────────────────────────────────────────────────────────────

-- The warehouse. Written ONLY by our parser (ADR 0002).
--
-- NEVER point the game's "Export data directly into a MySQL database" here. Its
-- own dialog warns that it overwrites colliding table names, and mixing
-- vendor-exported tables with parsed ones destroys the provenance line that
-- makes a data incident triageable.
CREATE DATABASE IF NOT EXISTS ootp
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- Ground truth, exported by the game from a DISPOSABLE STANDARD-MODE save — the
-- export does not exist in Challenge Mode (docs/data-access.md §6). Two
-- databases rather than one because the export drops tables on the way in, so a
-- second export into a shared database destroys the first.
CREATE DATABASE IF NOT EXISTS ootp_truth_real
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS ootp_truth_osa
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- utf8mb4 is load-bearing, not decorative. The export is configured with
-- "Replace accents" OFF so that names arrive intact, and names are a validation
-- surface against names.dat. A narrower charset would corrupt exactly the field
-- we intend to check.

-- ── Application user ────────────────────────────────────────────────────────

-- localhost only: the warehouse is local by decision (ADR 0004) and has no
-- reason to accept a connection from anywhere else.
CREATE USER IF NOT EXISTS 'ootp_ai'@'localhost' IDENTIFIED BY 'CHANGE_ME';

-- Database-scoped. No global privileges, no GRANT OPTION.
GRANT ALL PRIVILEGES ON ootp.*            TO 'ootp_ai'@'localhost';
GRANT ALL PRIVILEGES ON ootp_truth_real.* TO 'ootp_ai'@'localhost';
GRANT ALL PRIVILEGES ON ootp_truth_osa.*  TO 'ootp_ai'@'localhost';

FLUSH PRIVILEGES;
