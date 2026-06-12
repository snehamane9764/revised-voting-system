from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from voting_system.controller import RevisedVotingSystem
from voting_system.database import Candidate, Voter, VotingDatabase
from voting_system.iris_recognition import IrisRecognizer


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
DB_PATH = ROOT / "revised_voting.db"


class RevisedVotingBooth(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Revised Voting System")
        self.geometry("1120x760")
        self.minsize(980, 680)

        self.database = VotingDatabase(DB_PATH)
        self.system = RevisedVotingSystem(self.database)
        self.current_voter: Voter | None = None
        self.candidates: list[Candidate] = []
        self.capture_process: subprocess.Popen[str] | None = None
        self.biometric_process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str] = queue.Queue()

        self.status_text = tk.StringVar(value="Ready for voter verification")
        self.voter_text = tk.StringVar(value="No voter verified")
        self.barricade_text = tk.StringVar(value="BARRICADE LOCKED")
        self.selected_option: int | None = None
        self.pulse_step = 0

        self._configure_styles()
        self._build_layout()
        self.reset_sample_data(show_message=False)
        self.after(100, self._drain_output_queue)
        self.after(120, self._animate_status_canvas)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Root.TFrame", background="#e8e8e8")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("Panel.TLabelframe", background="#ffffff", foreground="#000000")
        style.configure(
            "Panel.TLabelframe.Label",
            background="#ffffff",
            foreground="#000000",
            font=("Helvetica", 12, "bold"),
        )
        style.configure("Primary.TButton", font=("Helvetica", 13, "bold"), padding=(16, 12))
        style.configure("Secondary.TButton", font=("Helvetica", 12), padding=(12, 9))
        style.configure("Title.TLabel", background="#e8e8e8", foreground="#000000")
        style.configure("Muted.TLabel", background="#e8e8e8", foreground="#444444")

    def _build_layout(self) -> None:
        self.configure(bg="#e8e8e8")

        header = tk.Frame(self, bg="#000000", padx=26, pady=18)
        header.pack(fill="x")
        header_top = tk.Frame(header, bg="#000000")
        header_top.pack(fill="x")

        tk.Label(
            header_top,
            text="Revised Voting System",
            fg="white",
            bg="#000000",
            font=("Helvetica", 28, "bold"),
        ).pack(side="left", anchor="w")
        self.status_canvas = tk.Canvas(header_top, width=210, height=54, bg="#000000", highlightthickness=0)
        self.status_canvas.pack(side="right")
        tk.Label(
            header,
            text="Biometric verification | Automated barricade | Contactless EVM",
            fg="#d0d0d0",
            bg="#000000",
            font=("Helvetica", 13),
        ).pack(anchor="w", pady=(3, 0))

        body = ttk.Frame(self, padding=20, style="Root.TFrame")
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, style="Root.TFrame")
        left.pack(side="left", fill="y", padx=(0, 18))

        voter_box = ttk.LabelFrame(left, text="Voter Access", padding=16, style="Panel.TLabelframe")
        voter_box.pack(fill="x")
        ttk.Label(voter_box, textvariable=self.voter_text, wraplength=280, font=("Helvetica", 12)).pack(anchor="w")
        ttk.Button(voter_box, text="Enroll My Biometric", command=self.enroll_biometric, style="Secondary.TButton").pack(
            fill="x", pady=(12, 5)
        )
        ttk.Button(voter_box, text="Verify and Open Barricade", command=self.verify_voter, style="Primary.TButton").pack(
            fill="x", pady=5
        )
        ttk.Button(voter_box, text="Reset Booth", command=self.reset_sample_data, style="Secondary.TButton").pack(
            fill="x", pady=5
        )

        camera_box = ttk.LabelFrame(left, text="Vote Capture", padding=16, style="Panel.TLabelframe")
        camera_box.pack(fill="x", pady=(16, 0))
        ttk.Button(camera_box, text="Capture Vote", command=self.capture_vote, style="Primary.TButton").pack(
            fill="x", pady=5
        )

        status_box = ttk.LabelFrame(left, text="Booth Status", padding=16, style="Panel.TLabelframe")
        status_box.pack(fill="both", expand=True, pady=(16, 0))
        tk.Label(
            status_box,
            textvariable=self.barricade_text,
            bg="#000000",
            fg="#ffffff",
            font=("Helvetica", 14, "bold"),
            padx=12,
            pady=10,
        ).pack(fill="x", pady=(0, 12))
        ttk.Label(status_box, textvariable=self.status_text, wraplength=280, font=("Helvetica", 12, "bold")).pack(anchor="w")

        right = ttk.Frame(body, style="Root.TFrame")
        right.pack(side="left", fill="both", expand=True)

        top_row = ttk.Frame(right, style="Root.TFrame")
        top_row.pack(fill="x", pady=(0, 10))
        ttk.Label(top_row, text="EVM Candidate List", font=("Helvetica", 21, "bold"), style="Title.TLabel").pack(
            side="left", anchor="w"
        )
        ttk.Label(
            top_row,
            text="Show the matching gesture number to vote",
            font=("Helvetica", 12),
            style="Muted.TLabel",
        ).pack(side="right", anchor="e")

        evm_content = ttk.Frame(right, style="Root.TFrame")
        evm_content.pack(fill="both", expand=True)

        machine_panel = tk.Frame(
            evm_content,
            bg="#d8d8d8",
            highlightbackground="#000000",
            highlightthickness=2,
            padx=12,
            pady=12,
        )
        machine_panel.pack(side="left", fill="y", padx=(0, 14))
        tk.Label(
            machine_panel,
            text="ELECTRONIC VOTING MACHINE",
            bg="#d8d8d8",
            fg="#000000",
            font=("Helvetica", 11, "bold"),
        ).pack(pady=(0, 8))
        self.evm_canvas = tk.Canvas(
            machine_panel,
            width=260,
            height=500,
            bg="#f7f7f7",
            highlightbackground="#000000",
            highlightthickness=1,
        )
        self.evm_canvas.pack()
        self.draw_evm_machine()

        self.candidate_frame = ttk.Frame(evm_content, style="Root.TFrame")
        self.candidate_frame.pack(side="left", fill="both", expand=True)
        self.render_empty_candidates()

    def draw_evm_machine(self, selected_option: int | None = None) -> None:
        canvas = self.evm_canvas
        canvas.delete("all")
        canvas.create_rectangle(16, 14, 244, 486, fill="#e6e6e6", outline="#000000", width=3)
        canvas.create_rectangle(32, 32, 228, 112, fill="#111111", outline="#000000", width=2)

        if selected_option and 1 <= selected_option <= len(self.candidates):
            candidate = self.candidates[selected_option - 1]
            canvas.create_text(130, 55, text=f"OPTION {selected_option} SELECTED", fill="#ffffff", font=("Helvetica", 12, "bold"))
            canvas.create_text(130, 82, text=candidate.name, fill="#ffffff", font=("Helvetica", 11), width=180)
            canvas.create_text(130, 101, text=candidate.party, fill="#cccccc", font=("Helvetica", 9), width=180)
        elif self.current_voter:
            canvas.create_text(130, 62, text="EVM READY", fill="#ffffff", font=("Helvetica", 15, "bold"))
            canvas.create_text(130, 88, text="SHOW GESTURE TO SELECT", fill="#cccccc", font=("Helvetica", 9))
        else:
            canvas.create_text(130, 62, text="EVM LOCKED", fill="#ffffff", font=("Helvetica", 15, "bold"))
            canvas.create_text(130, 88, text="BIOMETRIC ACCESS REQUIRED", fill="#cccccc", font=("Helvetica", 9))

        for option in range(1, 11):
            row_y = 137 + (option - 1) * 32
            is_selected = option == selected_option
            canvas.create_rectangle(40, row_y, 220, row_y + 24, fill="#ffffff", outline="#777777")
            canvas.create_text(60, row_y + 12, text=str(option), fill="#000000", font=("Helvetica", 11, "bold"))
            canvas.create_line(82, row_y + 4, 82, row_y + 20, fill="#aaaaaa")
            canvas.create_text(100, row_y + 12, text="NOTA" if option == 10 else f"CANDIDATE {option}", anchor="w", fill="#000000", font=("Helvetica", 9))
            canvas.create_oval(
                190,
                row_y + 4,
                208,
                row_y + 22,
                fill="#000000" if is_selected else "#ffffff",
                outline="#000000",
                width=2,
            )

        canvas.create_text(130, 474, text="CONTROL UNIT - BALLOT UNIT", fill="#333333", font=("Helvetica", 8, "bold"))

    def _animate_status_canvas(self) -> None:
        canvas = self.status_canvas
        canvas.delete("all")
        self.pulse_step = (self.pulse_step + 1) % 36
        radius = 10 + (self.pulse_step % 18)
        color = "#ffffff" if self.current_voter else "#777777"
        canvas.create_oval(14, 14, 14 + radius * 2, 14 + radius * 2, outline=color, width=2)
        canvas.create_oval(28, 28, 48, 48, fill="#ffffff" if self.current_voter else "#555555", outline="")
        canvas.create_text(
            114,
            37,
            text="ACCESS UNLOCKED" if self.current_voter else "ACCESS LOCKED",
            fill="white",
            font=("Helvetica", 13, "bold"),
        )
        self.after(120, self._animate_status_canvas)

    def render_empty_candidates(self) -> None:
        self.clear_candidates()
        frame = tk.Frame(self.candidate_frame, bg="#ffffff", highlightbackground="#999999", highlightthickness=1)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text="Verify voter to unlock the EVM panel",
            bg="#ffffff",
            fg="#000000",
            font=("Helvetica", 18, "bold"),
        ).pack(pady=(120, 8))
        tk.Label(
            frame,
            text="The candidate list appears here after iris verification.",
            bg="#ffffff",
            fg="#555555",
            font=("Helvetica", 13),
        ).pack()

    def render_candidates(self) -> None:
        self.clear_candidates()
        for index, candidate in enumerate(self.candidates, start=1):
            is_selected = index == self.selected_option
            row = tk.Frame(
                self.candidate_frame,
                bg="#dddddd" if is_selected else "#ffffff",
                highlightbackground="#000000",
                highlightthickness=3 if is_selected else 1,
                padx=12,
                pady=7,
            )
            row.pack(fill="x", pady=3)

            number = tk.Label(
                row,
                text=str(index),
                bg="#000000",
                fg="white",
                width=4,
                font=("Helvetica", 18, "bold"),
            )
            number.pack(side="left", padx=(0, 14))

            row_background = "#dddddd" if is_selected else "#ffffff"
            text = tk.Frame(row, bg=row_background)
            text.pack(side="left", fill="x", expand=True)
            tk.Label(
                text,
                text=candidate.name,
                bg=row_background,
                fg="#000000",
                font=("Helvetica", 16, "bold"),
            ).pack(anchor="w")
            tk.Label(
                text,
                text=candidate.party,
                bg=row_background,
                fg="#555555",
                font=("Helvetica", 12),
            ).pack(anchor="w")

            tk.Label(
                row,
                text="SELECTED" if is_selected else f"Gesture {index}",
                bg="#000000" if is_selected else "#eeeeee",
                fg="#ffffff" if is_selected else "#000000",
                font=("Helvetica", 13, "bold"),
                padx=12,
                pady=6,
            ).pack(side="right")

    def clear_candidates(self) -> None:
        for child in self.candidate_frame.winfo_children():
            child.destroy()

    def reset_sample_data(self, show_message: bool = True) -> None:
        result = subprocess.run(
            [PYTHON, "scripts/seed_database.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            messagebox.showerror("Setup failed", result.stdout + result.stderr)
            return

        self.current_voter = None
        self.candidates = []
        self.selected_option = None
        self.voter_text.set("No voter verified")
        self.barricade_text.set("BARRICADE LOCKED")
        self.status_text.set("")
        self.draw_evm_machine()
        self.render_empty_candidates()
        if show_message:
            messagebox.showinfo("Ready", "Sample voter database has been reset.")

    def enroll_biometric(self) -> None:
        if self.biometric_process and self.biometric_process.poll() is None:
            messagebox.showinfo("Biometric camera", "Biometric capture is already running.")
            return

        template_path = ROOT / "data/biometric/voter001.png"
        command = [
            PYTHON,
            "biometric_camera.py",
            "--mode",
            "enroll",
            "--template",
            str(template_path),
        ]
        self.status_text.set("Biometric enrollment camera opened. Look directly at the Mac camera.")
        threading.Thread(target=self._run_biometric, args=(command,), daemon=True).start()

    def verify_voter(self) -> None:
        template_path = ROOT / "data/biometric/voter001.png"
        if not template_path.exists():
            messagebox.showwarning("Enrollment required", "Enroll your biometric before verification.")
            return
        if self.biometric_process and self.biometric_process.poll() is None:
            messagebox.showinfo("Biometric camera", "Biometric capture is already running.")
            return

        command = [
            PYTHON,
            "biometric_camera.py",
            "--mode",
            "verify",
            "--template",
            str(template_path),
        ]
        self.status_text.set("Biometric verification started. Look directly at the Mac camera.")
        threading.Thread(target=self._run_biometric, args=(command,), daemon=True).start()

    def _run_biometric(self, command: list[str]) -> None:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.biometric_process = process
        if process.stdout:
            for line in process.stdout:
                self.output_queue.put(line.strip())
        process.wait()
        self.output_queue.put("__BIOMETRIC_DONE__")

    def complete_voter_verification(self, score: str) -> None:
        probe_path = ROOT / "data/iris_templates/scan_voter001.txt"
        probe = IrisRecognizer.read_template(probe_path)
        verification = self.system.verify_voter(probe)

        if not verification.allowed or verification.voter is None:
            self.current_voter = None
            self.candidates = []
            self.selected_option = None
            self.voter_text.set("No voter verified")
            self.barricade_text.set("BARRICADE LOCKED")
            self.status_text.set(verification.message)
            self.draw_evm_machine()
            self.render_empty_candidates()
            messagebox.showwarning("Verification failed", verification.message)
            return

        self.current_voter = verification.voter
        self.candidates = self.system.candidates_for_voter(verification.voter)
        self.selected_option = None
        self.voter_text.set(
            f"{verification.voter.full_name}\n"
            f"Constituency: {verification.voter.constituency}\n"
            "Status: Verified"
        )
        self.barricade_text.set("BARRICADE UNLOCKED")
        self.status_text.set(f"Biometric verified (score {score}). Barricade unlocked.")
        self.draw_evm_machine()
        self.render_candidates()
        messagebox.showinfo(
            "Access Granted",
            "Biometric verification successful.\n\nBarricade unlocked. You may now cast your vote.",
        )

    def capture_vote(self) -> None:
        if self.current_voter is None:
            messagebox.showwarning("Verify voter", "Please verify the voter before capturing a vote.")
            return
        if not self.candidates:
            messagebox.showwarning("No candidates", "Candidate list is not available.")
            return
        if self.capture_process and self.capture_process.poll() is None:
            messagebox.showinfo("Gesture running", "Gesture capture is already open.")
            return

        command = [
            PYTHON,
            "webcam_gesture_demo.py",
            "--selection-mode",
            "--max-selection",
            str(len(self.candidates)),
        ]
        self.status_text.set("Gesture camera opened. Hold your option number steady.")
        threading.Thread(target=self._run_gesture_capture, args=(command,), daemon=True).start()

    def _run_gesture_capture(self, command: list[str]) -> None:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.capture_process = process
        if process.stdout:
            for line in process.stdout:
                self.output_queue.put(line.strip())
        process.wait()
        self.output_queue.put("__CAPTURE_DONE__")

    def _drain_output_queue(self) -> None:
        while True:
            try:
                message = self.output_queue.get_nowait()
            except queue.Empty:
                break

            if message.startswith("FINAL_SELECTION:"):
                option = int(message.split(":", 1)[1])
                self.after(0, lambda selected=option: self.confirm_vote(selected))
            elif message.startswith("BIOMETRIC_ENROLLED:"):
                self.status_text.set("Biometric enrollment completed. You can now verify the voter.")
                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Enrollment Complete",
                        "Your biometric template was captured locally. Click Verify and Open Barricade.",
                    ),
                )
            elif message.startswith("BIOMETRIC_VERIFIED:"):
                score = message.split(":", 1)[1]
                self.after(0, lambda match_score=score: self.complete_voter_verification(match_score))
            elif message.startswith("BIOMETRIC_ERROR:"):
                error = message.split(":", 1)[1]
                self.status_text.set(error)
                self.after(0, lambda detail=error: messagebox.showerror("Biometric error", detail))
            elif message == "__CAPTURE_DONE__":
                if self.status_text.get().startswith("Gesture camera opened"):
                    self.status_text.set("Gesture capture closed.")
            elif message == "__BIOMETRIC_DONE__":
                if self.status_text.get().startswith("Biometric verification started"):
                    self.status_text.set("Biometric verification closed without a match.")
            elif message:
                self.status_text.set(message)

        self.after(100, self._drain_output_queue)

    def confirm_vote(self, option: int) -> None:
        if self.current_voter is None:
            return
        if option < 1 or option > len(self.candidates):
            messagebox.showwarning("Invalid option", f"Gesture option {option} is not available.")
            return

        candidate = self.candidates[option - 1]
        self.selected_option = option
        self.draw_evm_machine(option)
        self.render_candidates()
        self.status_text.set(f"Option {option} selected: {candidate.name} ({candidate.party}). Awaiting confirmation.")
        self.update_idletasks()
        confirmed = messagebox.askyesno(
            "Confirm Vote",
            f"You selected option {option}:\n\n"
            f"{candidate.name}\n{candidate.party}\n\n"
            "Do you want to cast this vote?",
        )
        if not confirmed:
            self.selected_option = None
            self.draw_evm_machine()
            self.render_candidates()
            self.status_text.set("Vote cancelled. Capture gesture again if needed.")
            return

        try:
            self.database.cast_vote(self.current_voter.voter_id, candidate.candidate_id)
        except ValueError as error:
            messagebox.showerror("Vote failed", str(error))
            self.status_text.set(str(error))
            return

        message = f"Voting has been recorded for {candidate.name} ({candidate.party})."
        self.status_text.set(message)
        messagebox.showinfo("Vote Recorded", message)
        self.current_voter = None
        self.barricade_text.set("BARRICADE LOCKED")
        self.voter_text.set(
            f"Vote completed\n"
            f"Selected option: {option}\n"
            f"{candidate.name} - {candidate.party}"
        )
        self.draw_evm_machine(option)
        self.render_candidates()


if __name__ == "__main__":
    app = RevisedVotingBooth()
    app.mainloop()
