import { useState } from "react";

const SIGNATURE_MEANINGS = [
  { value: "review", label: "Review" },
  { value: "approval", label: "Approval" },
  { value: "responsibility", label: "Responsibility" },
  { value: "authorship", label: "Authorship" },
  { value: "verification", label: "Verification" },
];

export default function CertificationModal({ reportId, onClose, onSuccess }) {
  const [password, setPassword] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [signatureMeaning, setSignatureMeaning] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!signatureMeaning) {
      setError("Signature meaning is required (21 CFR Part 11 §11.50)");
      return;
    }

    setLoading(true);
    try {
      const body = {
        password,
        signature_meaning: signatureMeaning,
        notes,
      };
      if (otpCode) {
        body.otp_code = otpCode;
      }

      const res = await fetch(`/api/reports/${reportId}/sign/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Certification failed");
        return;
      }
      onSuccess?.(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>Certify Report</h2>
        <p>21 CFR Part 11 — Electronic Signature</p>

        <form onSubmit={handleSubmit}>
          <label>
            Signature Meaning *
            <select
              value={signatureMeaning}
              onChange={(e) => setSignatureMeaning(e.target.value)}
              required
            >
              <option value="">-- Select meaning --</option>
              {SIGNATURE_MEANINGS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Password *
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>

          <label>
            OTP Code (if 2FA enabled)
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value)}
            />
          </label>

          <label>
            Notes
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
          </label>

          {error && <div className="error-message">{error}</div>}

          <div className="modal-actions">
            <button type="button" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" disabled={loading}>
              {loading ? "Signing..." : "Sign & Certify"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
