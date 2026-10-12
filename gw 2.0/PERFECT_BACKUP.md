# Item 81 — The perfect backup: unreadable to a thief, never a lockout

Opened 2026-10-12. Rob: *"Will the backups hold a crypto key that other groundwork version understand? I don't want
someone taking a backup and installing groundwork on another machine and steal the user data and I also don't want a
user locked out because they took a backup don't remember the password and they are also locked out of their data. We
need something that the user would be able to do to restore their data but keep it uncompromised. The perfect
backup."*

**B1-B10 RULED 2026-10-12** (Rob: *"I agree adding a B10 would do it. I do have a one to test with. I approve b1-b10
if a user never uses the health they may not care about the extra protection."*):
- B1-B9 as recommended.
- **B10 stays optional.** It is offered to everyone, and suggested when the person has health spending or records.
  Someone who never uses health tracking may skip it.
- Rob has a security key to test it with.
- 1.x was asked and not answered, so it stays master only, the default, until Rob says otherwise.
- **Builds after item 45 stage 1 (H6) is accepted.**

## 1. What is true today (measured 2026-10-12, master)

- **A backup is a plain copy of the database:** `shutil.copy2(DB_PATH, ...)` in `/api/backup/create`. Anyone who has
  the file can open it with any SQLite tool, or restore it into any Groundwork on any computer. **Nothing protects
  it.**
- **Backups go where the person points them:** the data folder by default, or a USB drive (Settings → Data &
  Backup). Item 62 already leaves the AI log out unless it is ticked.
- **The live database (`groundwork.db`) is not encrypted either.** Someone with the person's computer account can read
  it. Backups are the copies that travel (USB drives, other computers), so they come first.
- **What the app already has:**
  - the operating system's vault (`keyring`, item 57: bank logins live there, never in Groundwork's files);
  - the `cryptography` library, already installed alongside the PDF reader.

## 2. The tension, and how this resolves it

*"Unreadable without a secret"* and *"never locked out"* pull against each other. **No design can have both if the
secret is one password**: lose it and the data is gone, which is the point of encryption. The way out is **more than
one key to the same lock**, each kept somewhere different:

| Key | Who holds it | Opens a backup... |
|---|---|---|
| **1. This computer's vault** | The operating system, for this person's login | ...on **this** computer, with nothing to type |
| **2. A backup password** | The person's memory | ...on **any** computer |
| **3. A recovery key** (a short code, shown once, printed or written down) | A drawer, a safe, a wallet | ...on **any** computer, when the password is forgotten |

**A thief with the backup file, on another computer, has none of the three.** The file is unreadable, and Groundwork
on their machine can't open it either: the format is public, the keys are not.

**The person is locked out only if they lose all three at once:** the computer, the password, and the paper. That is
the one case no honest design can cover without keeping a copy of the key somewhere else, and keeping a copy anywhere
else means someone else could read the data.

## 3. Points for ruling

**B1. Backups are encrypted, always.**
- Each backup is sealed with AES-256-GCM using one random *backup key*.
- GCM also detects tampering and corruption: a damaged or altered backup says so instead of restoring bad data.

*Recommended.*

**B2. Three ways in (§2's table).**
- The backup key is never stored in the clear. It is stored **wrapped**, inside each backup's header:
  - once by the backup password (stretched with scrypt, so guessing is slow);
  - once by the recovery key.
- A copy also sits in this computer's vault, so restoring on the same computer asks for nothing.
- **Groundwork never sends any key anywhere.** There is no server copy, and no "forgot password" that goes through
  anyone.

*Recommended.* That last part is what keeps it uncompromised.

**B3. Setting it up, once.** The first time backups are turned on:
- the person chooses a backup password (at least 10 characters; no hint is stored, since a hint helps a thief too);
- Groundwork shows the **recovery key** once, as 24 plain words, with **Print** and *"I've written it down"*;
- it asks for 3 of the words back, to prove it was saved.

The recovery key is never stored by Groundwork, not even in the vault.

*Recommended.*

**B4. Restoring.**
- **On this computer:** nothing to type.
- **On a new computer:** the backup password, or the recovery key.
- **A wrong password** says so plainly and offers the recovery key.
- **A restore never overwrites the current data without the existing safety copy** (the restore flow already makes
  one).

*Recommended.*

**B5. Any Groundwork can read the format, and no Groundwork can read it without a key.**
- Each backup starts with a versioned header (`GWBK1`) that says how it was sealed, so future versions open today's
  backups.
- A **"Check this backup"** button proves a backup opens, and isn't damaged, without restoring it.

*Recommended.* This answers "a crypto key that other Groundwork versions understand": the versions understand the
format; the key stays the person's.

**B6. Changing the password, or replacing the recovery key.**
- **New password:** new backups use it. Older backups still open with the old password, or with the recovery key.
- **New recovery key** (if the paper is lost): the next backup uses it, and Groundwork says plainly that older
  backups still need the old one, or the password.

*Recommended.*

**B7. Old plain backups.**
- Groundwork lists the unencrypted backups it can see and offers to **re-save each one encrypted**.
- **Deleting the plain copies** is offered separately and is the person's tap. Groundwork never deletes them on its
  own.

*Recommended.*

**B8. If the person forgets the password and has lost the paper, but still has this computer.** The vault still
opens the backups here. Groundwork offers to set a new password and a new recovery key, and re-seal.

*Recommended.* This is the third key doing its job.

**B9. Tests.** A test that a backup:
- is unreadable as SQLite without a key;
- opens with each of the three keys, and not with a wrong one;
- detects tampering;
- survives a password change;
- opens in a fresh Groundwork (a new temporary vault) only with the password or recovery key.

Plus: no key ever written to a log, export, the AI log or the network (it joins H6's sink registry).

*Recommended.*

**B10. Two-factor, done the way a file allows: an optional security key.** Rob asked for 2FA on restoring, like a
Google push approval: *"I don't know if it ever would work like that."*

- **Why a push approval can't protect a file.**
  - Google's push works because Google's servers are part of the lock: the sign-in can't finish without them.
  - A backup is a file. A thief needn't ask Groundwork anything: they can try to open it offline, with their own
    program. A "wait for approval" step inside Groundwork, they would simply skip.
  - For a push to really stop them, a server would have to hold part of every user's key. That is a third party in
    the loop, and if that server ever went away, every backup would be locked.
- **Why authenticator codes don't help either.** Groundwork would have to keep the code's secret to check it, so the
  thief would have it too.
- **What does work offline: a physical security key** (a FIDO2 key such as a YubiKey, using its hmac-secret
  feature).
  - When it is turned on, opening a backup on another computer needs **the password and the key, plugged in and
    touched**.
  - The key's secret never leaves it. A thief with the file and the password still can't open it.
  - It is real cryptography, not a prompt: it works offline, with no server.
- **No lockout.**
  - The recovery key (B3) still opens everything if the security key is lost.
  - This computer's vault still opens its own backups with nothing to type.
  - Registering a second security key as a spare is offered.
- **Optional:** turned on by the person, never required.

*Offered.* It adds the `fido2` library and needs a key to test on.

## 4. Not decided here

- **Encrypting the live database** (`groundwork.db`, for example with SQLCipher). That is a larger change: every
  read, the installer, and recovery. It is a separate item, and this one makes the portable copies safe first.
- **Cloud backup** of any kind. Not proposed: no third party sees the data.
- **1.x:** master only, unless Rob rules that unencrypted backups are a security fix under L1. That is his call; it
  would then ship as a 1.1.x release.
