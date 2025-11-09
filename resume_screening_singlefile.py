# File: resume_screening_designed_singlefile.py
"""
AI Resume Screening & Auto-Reply System (Single-file, Designed GUI)

Features:
- Upload multiple resumes (.pdf, .docx, .txt)
- Enter required skills and critical skills
- Keyword-based skill extraction
- Classification with highlighted rules:
    ✅ Suitable  : match% >= 70%
    ⚠ Maybe     : 40% <= match% < 70%
    ❌ Reject    : match% < 40% OR missing any critical skill
- Color-coded Treeview results (green/orange/red)
- Big badge for selected candidate classification
- Generate editable reply templates, save drafts, export CSV

Run:
 python resume_screening_designed_singlefile.py

Dependencies:
 pip install PyPDF2 python-docx
"""

import os
import re
import json
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from datetime import datetime

# Optional external libs for reading files
try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

try:
    import docx
except Exception:
    docx = None

# ---------------- Config ----------------
DRAFTS_FILE = "resume_reply_drafts.json"
EXPORT_CSV = "screening_results.csv"
SUPPORTED_EXT = (".pdf", ".docx", ".txt")

DEFAULT_REQUIRED_SKILLS = "python, machine learning, sql, aws"
DEFAULT_CRITICAL_SKILLS = ""  # leave blank by default

# ---------------- Helpers: file reading ----------------
def read_pdf_text(path):
    if PdfReader is None:
        raise RuntimeError("PyPDF2 is not installed. Install with: pip install PyPDF2")
    try:
        reader = PdfReader(path)
        texts = []
        for page in reader.pages:
            try:
                t = page.extract_text() or ""
                texts.append(t)
            except Exception:
                pass
        return "\n".join(texts)
    except Exception as e:
        raise e

def read_docx_text(path):
    if docx is None:
        raise RuntimeError("python-docx is not installed. Install with: pip install python-docx")
    try:
        d = docx.Document(path)
        paras = [p.text for p in d.paragraphs if p.text]
        return "\n".join(paras)
    except Exception as e:
        raise e

def read_txt_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        raise e

def extract_text_from_file(path):
    lower = path.lower()
    if lower.endswith(".pdf"):
        return read_pdf_text(path)
    elif lower.endswith(".docx"):
        return read_docx_text(path)
    elif lower.endswith(".txt"):
        return read_txt_text(path)
    else:
        raise ValueError("Unsupported file type: " + path)

# ---------------- Helpers: skills matching ----------------
def normalize_text_for_matching(text):
    t = text.lower()
    t = re.sub(r"[^a-z0-9\+\#]+", " ", t)
    return " " + t + " "

def find_skill_matches(text, skills_list):
    t = normalize_text_for_matching(text)
    found = set()
    for kw in skills_list:
        kw = kw.strip().lower()
        if not kw:
            continue
        if " " in kw:
            if kw in t:
                found.add(kw)
        else:
            patt = r"\b" + re.escape(kw) + r"\b"
            if re.search(patt, t):
                found.add(kw)
    return sorted(found)

def compute_match_percentage(required_skills, found_skills):
    if not required_skills:
        return 0.0, 0, 0
    total = len(required_skills)
    matched = sum(1 for s in required_skills if s in found_skills)
    pct = (matched / total) * 100.0
    return round(pct, 2), matched, total

# ---------------- Classification logic (HIGHLIGHTED) ----------------
def classify_by_required_skills(required_skills, found_skills, critical_skills):
    """
    HIGHLIGHTED RULES:
    - ✅ If match% >= 70% -> 'Suitable'
    - ⚠️ If 40% <= match% < 70% -> 'Maybe'
    - ❌ If match% < 40% OR any critical skill is missing -> 'Reject'
    """
    match_pct, matched, total = compute_match_percentage(required_skills, found_skills)
    missing_critical = [c for c in critical_skills if c not in found_skills and c.strip() != ""]
    if missing_critical:
        classification = "Reject"
        reason = f"Missing critical skills: {', '.join(missing_critical)}"
    else:
        if match_pct >= 70.0:
            classification = "Suitable"
            reason = f"{matched}/{total} required skills matched ({match_pct}%)"
        elif match_pct >= 40.0:
            classification = "Maybe"
            reason = f"{matched}/{total} required skills matched ({match_pct}%)"
        else:
            classification = "Reject"
            reason = f"{matched}/{total} required skills matched ({match_pct}%)"
    return classification, match_pct, reason

# ---------------- Reply template ----------------
def generate_reply_template(name, classification, top_skills, match_pct):
    if classification == "Suitable":
        body = (
            f"Hi {name or 'Candidate'},\n\n"
            f"Thank you for applying. We reviewed your resume and your skills ({', '.join(top_skills[:6]) or 'relevant skills'}) "
            f"show a strong fit for the role (match: {match_pct}%). We'll move your application to the next stage and contact you soon "
            "with interview details.\n\nBest regards,\nRecruitment Team"
        )
    elif classification == "Maybe":
        body = (
            f"Hi {name or 'Candidate'},\n\n"
            f"Thank you for applying. We see potential fit based on your skills ({', '.join(top_skills[:5]) or 'listed skills'}). "
            f"Your match is {match_pct}%. We'll review further and may reach out for a short screening call.\n\nBest regards,\nRecruitment Team"
        )
    else:
        body = (
            f"Hi {name or 'Candidate'},\n\n"
            "Thank you for applying. At this time we will not be proceeding with your application. "
            "We appreciate your interest and encourage you to apply for future openings that match your experience.\n\n"
            "Best regards,\nRecruitment Team"
        )
    return body

# ---------------- Persistence ----------------
def save_draft(d):
    drafts = []
    if os.path.exists(DRAFTS_FILE):
        try:
            with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
                drafts = json.load(f)
        except:
            drafts = []
    drafts.append(d)
    with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
        json.dump(drafts, f, indent=2, ensure_ascii=False)

# ---------------- GUI ----------------
class StyledResumeApp:
    def __init__(self, root):
        self.root = root
        root.title("Resume Screening & Auto-Reply — Designed")
        root.geometry("1180x760")
        root.configure(bg="#f5f7fb")

        self.resumes = []
        self.selected_index = None

        # Style
        self.style = ttk.Style(root)
        self.style.theme_use("clam")
        self.style.configure("TButton", padding=6)
        self.style.configure("Header.TLabel", font=("Helvetica", 14, "bold"), background="#f5f7fb")
        self.style.configure("Small.TLabel", font=("Helvetica", 10), background="#f5f7fb")
        self.style.configure("Rule.TFrame", background="#fff4dc")
        self.style.configure("Badge.TLabel", font=("Helvetica", 14, "bold"))

        # Top frame: title + controls
        top = tk.Frame(root, bg="#f5f7fb")
        top.pack(fill=tk.X, padx=12, pady=(12,6))

        title = tk.Label(top, text="AI Resume Screening & Auto-Reply", font=("Helvetica", 18, "bold"), bg="#f5f7fb")
        title.pack(side=tk.LEFT)

        controls = tk.Frame(top, bg="#f5f7fb")
        controls.pack(side=tk.RIGHT)

        ttk.Button(controls, text="Upload Resumes", command=self.upload_resumes).pack(side=tk.LEFT, padx=6)
        ttk.Button(controls, text="Screen Resumes", command=self.screen_resumes).pack(side=tk.LEFT, padx=6)
        ttk.Button(controls, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=6)
        ttk.Button(controls, text="Load Drafts", command=self.show_saved_drafts).pack(side=tk.LEFT, padx=6)

        # Middle frame: inputs & rules
        mid = tk.Frame(root, bg="#f5f7fb")
        mid.pack(fill=tk.X, padx=12, pady=(6,8))

        inputs = tk.Frame(mid, bg="#f5f7fb")
        inputs.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(inputs, text="Required skills (comma-separated):", bg="#f5f7fb").grid(row=0, column=0, sticky="w")
        self.req_entry = tk.Entry(inputs, width=60)
        self.req_entry.grid(row=0, column=1, sticky="w", padx=6)
        self.req_entry.insert(0, DEFAULT_REQUIRED_SKILLS)

        tk.Label(inputs, text="Critical skills (comma-separated):", bg="#f5f7fb").grid(row=1, column=0, sticky="w", pady=(6,0))
        self.crit_entry = tk.Entry(inputs, width=60)
        self.crit_entry.grid(row=1, column=1, sticky="w", padx=6, pady=(6,0))
        self.crit_entry.insert(0, DEFAULT_CRITICAL_SKILLS)

        # Rules panel (highlighted)
        rules_frame = tk.Frame(mid, bg="#fff4dc", bd=1, relief=tk.SOLID)
        rules_frame.pack(side=tk.RIGHT, padx=(12,0), pady=0)
        tk.Label(rules_frame, text="Classification Rules (HIGHLIGHTED)", bg="#fff4dc", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=8, pady=(6,0))
        tk.Label(rules_frame, text="✅ If the candidate has most of the required skills (≥ 70%) → Suitable", bg="#fff4dc", anchor="w").pack(anchor="w", padx=12, pady=(6,0))
        tk.Label(rules_frame, text="⚠️ If candidate has some matching skills (40% — 69%) → Maybe", bg="#fff4dc").pack(anchor="w", padx=12, pady=(4,0))
        tk.Label(rules_frame, text="❌ If candidate has less than 40% match OR missing any critical skill → Reject", bg="#fff4dc").pack(anchor="w", padx=12, pady=(4,10))

        # Main frame: left (list) / right (details)
        main = tk.Frame(root, bg="#f5f7fb")
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0,12))

        # Left: Treeview for results
        left = tk.Frame(main, bg="#eef2f7")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0,8), pady=4)

        tk.Label(left, text="Screening Results", bg="#eef2f7", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=8, pady=(8,4))

        cols = ("#1", "#2", "#3")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=28)
        self.tree.heading("#1", text="Candidate File")
        self.tree.heading("#2", text="Classification")
        self.tree.heading("#3", text="Match %")
        self.tree.column("#1", width=280)
        self.tree.column("#2", width=110, anchor="center")
        self.tree.column("#3", width=80, anchor="center")
        self.tree.pack(padx=8, pady=(0,8))

        # Treeview tags for coloring
        self.tree.tag_configure("suitable", background="#e6f4ea")  # light green
        self.tree.tag_configure("maybe", background="#fff4e6")     # light orange
        self.tree.tag_configure("reject", background="#fdecea")    # light red

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # Right: details + badge + reply
        right = tk.Frame(main, bg="#f5f7fb")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Top right: badge + quick stats
        top_right = tk.Frame(right, bg="#f5f7fb")
        top_right.pack(fill=tk.X, padx=6, pady=(6,4))

        badge_frame = tk.Frame(top_right, bg="#f5f7fb")
        badge_frame.pack(side=tk.LEFT, padx=(0,12))

        self.badge_label = tk.Label(badge_frame, text="—", font=("Helvetica", 16, "bold"), width=18, relief=tk.RIDGE, bd=2, bg="#f0f0f0")
        self.badge_label.pack(padx=2, pady=2)

        stats_frame = tk.Frame(top_right, bg="#f5f7fb")
        stats_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.detail_summary = tk.Label(stats_frame, text="Select a candidate to see details", bg="#f5f7fb", anchor="w", justify="left")
        self.detail_summary.pack(fill=tk.X, padx=6)

        # Details text
        tk.Label(right, text="Candidate Details & Resume Preview", bg="#f5f7fb", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=6)
        self.details_box = scrolledtext.ScrolledText(right, width=80, height=14, wrap=tk.WORD)
        self.details_box.pack(fill=tk.BOTH, padx=6, pady=(4,8))
        self.details_box.config(state=tk.DISABLED)

        # Reply editor
        tk.Label(right, text="Generated Reply (editable)", bg="#f5f7fb", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=6)
        self.reply_box = scrolledtext.ScrolledText(right, width=80, height=10, wrap=tk.WORD)
        self.reply_box.pack(fill=tk.BOTH, padx=6, pady=(4,8))

        # Bottom actions
        bottom = tk.Frame(right, bg="#f5f7fb")
        bottom.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(bottom, text="Generate Reply for Selected", command=self.generate_reply_for_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(bottom, text="Save Reply Draft", command=self.save_reply_draft).pack(side=tk.LEFT, padx=6)
        ttk.Button(bottom, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(bottom, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=6)

        # Status bar
        self.status = tk.Label(root, text="Ready", bg="#f5f7fb", anchor="w")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        # Ensure drafts file exists
        if not os.path.exists(DRAFTS_FILE):
            with open(DRAFTS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)

    # ---------------- helpers ----------------
    def set_status(self, t):
        self.status.config(text=t)
        self.root.update_idletasks()

    # -------------- upload --------------
    def upload_resumes(self):
        paths = filedialog.askopenfilenames(title="Select resumes (.pdf, .docx, .txt)",
                                            filetypes=[("Documents", "*.pdf *.docx *.txt"), ("All files", "*.*")])
        if not paths:
            return
        added = 0
        for p in paths:
            if not p.lower().endswith(SUPPORTED_EXT):
                messagebox.showwarning("Unsupported", f"Skipping unsupported file: {p}")
                continue
            if any(r["path"] == p for r in self.resumes):
                continue
            name = os.path.basename(p)
            try:
                text = extract_text_from_file(p)
            except Exception as e:
                text = ""
                messagebox.showwarning("Read Error", f"Failed to read {name}: {e}")
            self.resumes.append({
                "path": p,
                "name": name,
                "text": text,
                "found_skills": [],
                "classification": "Unscreened",
                "match_pct": 0.0,
                "reason": ""
            })
            added += 1
        self.refresh_tree()
        self.set_status(f"Uploaded {added} files" if added else "No new files uploaded")

    def refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, r in enumerate(self.resumes):
            tag = r["classification"].lower() if r["classification"].lower() in ("suitable", "maybe", "reject") else ""
            self.tree.insert("", "end", iid=str(idx), values=(r["name"], r["classification"], f"{r['match_pct']}%"), tags=(tag,))

    # -------------- screening --------------
    def screen_resumes(self):
        if not self.resumes:
            messagebox.showinfo("No Files", "Upload resumes before screening.")
            return
        self.set_status("Screening resumes...")
        req_raw = self.req_entry.get().strip()
        crit_raw = self.crit_entry.get().strip()
        required_skills = [s.strip().lower() for s in req_raw.split(",") if s.strip()] if req_raw else []
        critical_skills = [s.strip().lower() for s in crit_raw.split(",") if s.strip()] if crit_raw else []

        for r in self.resumes:
            text = r["text"] or ""
            found = find_skill_matches(text, required_skills + critical_skills)
            r["found_skills"] = found
            classification, pct, reason = classify_by_required_skills(required_skills, found, critical_skills)
            r["classification"] = classification
            r["match_pct"] = pct
            r["reason"] = reason

        self.refresh_tree()
        self.set_status("Screening complete")
        messagebox.showinfo("Done", "Screening finished. Select an entry to view details.")

    # -------------- selection --------------
    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self.selected_index = idx
        r = self.resumes[idx]
        # Update badge
        if r["classification"] == "Suitable":
            self.badge_label.config(text="✔ Suitable", bg="#dff2e6", fg="#006b2e")
        elif r["classification"] == "Maybe":
            self.badge_label.config(text="⚠ Maybe", bg="#fff6e6", fg="#8a4f00")
        else:
            self.badge_label.config(text="✖ Reject", bg="#fdecea", fg="#8a1200")
        # Update summary
        summary = f"{r['name']} — {r['classification']} — {r['match_pct']}%\nReason: {r['reason']}"
        self.detail_summary.config(text=summary)
        # Show details
        self.show_candidate_details(r)
        # Clear reply until generated
        self.reply_box.delete(1.0, tk.END)

    def show_candidate_details(self, r):
        details = []
        details.append(f"File: {r['name']}")
        details.append(f"Path: {r['path']}")
        details.append(f"Classification: {r['classification']}")
        details.append(f"Match %: {r['match_pct']}%")
        details.append(f"Reason: {r['reason']}")
        details.append(f"Found skills ({len(r['found_skills'])}): {', '.join(r['found_skills']) if r['found_skills'] else 'None'}")
        details.append("\n--- Resume preview (first 1500 chars) ---\n")
        preview = (r['text'] or "")[:1500]
        if len(r['text'] or "") > 1500:
            preview += "\n\n...[truncated]"
        details.append(preview)
        self.details_box.config(state=tk.NORMAL)
        self.details_box.delete(1.0, tk.END)
        self.details_box.insert(tk.END, "\n".join(details))
        self.details_box.config(state=tk.DISABLED)

    # -------------- replies --------------
    def generate_reply_for_selected(self):
        if self.selected_index is None:
            messagebox.showinfo("Select Candidate", "Please select a candidate first.")
            return
        r = self.resumes[self.selected_index]
        name = self.heuristic_extract_name(r["text"]) or ""
        body = generate_reply_template(name, r["classification"], r.get("found_skills", []), r.get("match_pct", 0.0))
        self.reply_box.delete(1.0, tk.END)
        self.reply_box.insert(tk.END, body)

    def heuristic_extract_name(self, text):
        if not text:
            return None
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:8]
        for ln in lines:
            cleaned = re.sub(r"[^A-Za-z\s]", " ", ln).strip()
            parts = cleaned.split()
            if len(parts) >= 2 and parts[0].istitle() and parts[1].istitle():
                return " ".join(parts[:2])
        return None

    def save_reply_draft(self):
        if self.selected_index is None:
            messagebox.showinfo("Select Candidate", "Please select a candidate first.")
            return
        r = self.resumes[self.selected_index]
        reply = self.reply_box.get(1.0, tk.END).strip()
        if not reply:
            messagebox.showinfo("Empty", "Generate or type a reply before saving.")
            return
        draft = {
            "candidate_file": r["name"],
            "classification": r["classification"],
            "match_pct": r["match_pct"],
            "reply": reply,
            "saved_at": datetime.now().isoformat()
        }
        save_draft(draft)
        messagebox.showinfo("Saved", f"Reply draft saved to {DRAFTS_FILE}")

    def show_saved_drafts(self):
        if not os.path.exists(DRAFTS_FILE):
            messagebox.showinfo("No Drafts", "No drafts found.")
            return
        try:
            with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
                drafts = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read drafts: {e}")
            return
        if not drafts:
            messagebox.showinfo("No Drafts", "No drafts found.")
            return
        dw = tk.Toplevel(self.root)
        dw.title("Saved Drafts")
        dw.geometry("700x500")
        txt = scrolledtext.ScrolledText(dw, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True)
        out = []
        for i, d in enumerate(drafts):
            out.append(f"--- Draft {i+1} ---")
            out.append(f"Candidate File: {d.get('candidate_file')}")
            out.append(f"Classification: {d.get('classification')}")
            out.append(f"Match %: {d.get('match_pct')}")
            out.append(f"Saved at: {d.get('saved_at')}")
            out.append("")
            out.append(d.get("reply", ""))
            out.append("\n")
        txt.insert(tk.END, "\n".join(out))

    # -------------- export --------------
    def export_csv(self):
        if not self.resumes:
            messagebox.showinfo("No Data", "No screening results to export.")
            return
        try:
            with open(EXPORT_CSV, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["File", "Classification", "MatchPct", "Reason", "FoundSkills", "Path"])
                for r in self.resumes:
                    writer.writerow([r["name"], r["classification"], r["match_pct"], r["reason"], ";".join(r["found_skills"]), r["path"]])
            messagebox.showinfo("Exported", f"Results exported to {EXPORT_CSV}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV: {e}")

    # -------------- remove / clear --------------
    def remove_selected(self):
        if self.selected_index is None:
            messagebox.showinfo("Select Candidate", "Please select a candidate first.")
            return
        idx = self.selected_index
        name = self.resumes[idx]["name"]
        if messagebox.askyesno("Confirm", f"Remove {name} from list?"):
            del self.resumes[idx]
            self.selected_index = None
            self.refresh_tree()
            self.details_box.config(state=tk.NORMAL)
            self.details_box.delete(1.0, tk.END)
            self.details_box.config(state=tk.DISABLED)
            self.reply_box.delete(1.0, tk.END)
            self.badge_label.config(text="—", bg="#f0f0f0")
            self.detail_summary.config(text="Select a candidate to see details")
            self.set_status(f"Removed {name}")

    def clear_all(self):
        if not self.resumes:
            return
        if messagebox.askyesno("Confirm", "Clear all uploaded resumes?"):
            self.resumes = []
            self.selected_index = None
            self.refresh_tree()
            self.details_box.config(state=tk.NORMAL)
            self.details_box.delete(1.0, tk.END)
            self.details_box.config(state=tk.DISABLED)
            self.reply_box.delete(1.0, tk.END)
            self.badge_label.config(text="—", bg="#f0f0f0")
            self.detail_summary.config(text="Select a candidate to see details")
            self.set_status("Cleared all resumes")

# ---------------- main ----------------
def main():
    root = tk.Tk()
    app = StyledResumeApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
