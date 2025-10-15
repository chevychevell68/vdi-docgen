#!/usr/bin/env bash
set -euo pipefail

# ---------- Config ----------
APP_MODULE="${APP_MODULE:-app:app}"     # your Flask app import path
PORT="${PORT:-5000}"                    # port to bind
WORKERS="${WORKERS:-1}"                 # gunicorn workers
PYTHON="${PYTHON:-python3}"             # python interpreter
VENV_DIR="${VENV_DIR:-.venv}"           # virtualenv directory

TORCH_CPU_INDEX="https://download.pytorch.org/whl/cpu"

echo "[1/10] Python version:"
$PYTHON --version || true
pip --version || true

echo "[2/10] Creating virtual environment (${VENV_DIR})..."
if [ ! -d "${VENV_DIR}" ]; then
  $PYTHON -m venv "${VENV_DIR}"
fi
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

echo "[3/10] Upgrading pip..."
python -m pip install --upgrade pip wheel setuptools

# Small helper to try a command and return non-zero if it fails
try_install() {
  set +e
  echo "+ $*"
  "$@"
  local rc=$?
  set -e
  return $rc
}

# Parse python major.minor for compatibility hints
PY_MM="$(python - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
echo "[i] Detected Python ${PY_MM}"

echo "[4/10] Installing dependencies..."
if [ -f requirements.txt ]; then
  # If requirements mention torch/torchvision/torchaudio, install them first, safely.
  if grep -Ei '^(torch(|vision|audio))' requirements.txt >/dev/null 2>&1; then
    echo "[4a] Detected torch packages in requirements.txt — installing separately with CPU index and fallbacks"
    # Extract exact spec if present on a 'torch' line
    TORCH_SPEC_RAW="$(grep -E '^torch' requirements.txt | head -n1 || true)"
    # Default fallback versions by python version
    # PyTorch 2.5.x supports Python 3.12; use cpu wheels URL.
    FALLBACK_TORCH_VERSIONS=("torch==2.5.1" "torch==2.5.0" "torch==2.4.1")
    if [[ "${PY_MM}" == "3.12" ]]; then
      FALLBACK_TORCH_VERSIONS=("torch==2.5.1" "torch==2.5.0" "torch==2.4.1")
    fi
    # Normalize '+cpu' spec if present
    TORCH_SPEC_NORM=""
    if [[ -n "${TORCH_SPEC_RAW}" ]]; then
      # Strip comments and extras
      TORCH_SPEC_NORM="$(echo "${TORCH_SPEC_RAW}" | sed 's/[[:space:]]*#.*$//' | tr -d '\r')"
      # Remove any extras like +cpu from the spec; we'll supply the CPU index URL explicitly
      TORCH_SPEC_NORM="$(echo "${TORCH_SPEC_NORM}" | sed 's/+cpu//g')"
    fi
    echo "[i] torch spec from requirements: '${TORCH_SPEC_NORM:-<none>}'"

    # Try install using spec if present, else fallbacks
    INSTALLED_TORCH=0
    if [[ -n "${TORCH_SPEC_NORM}" ]]; then
      if try_install pip install --extra-index-url "${TORCH_CPU_INDEX}" "${TORCH_SPEC_NORM}"; then
        INSTALLED_TORCH=1
      else
        echo "[warn] Failed to install ${TORCH_SPEC_NORM} from CPU index; will try fallbacks..."
      fi
    fi
    if [[ "${INSTALLED_TORCH}" -eq 0 ]]; then
      for spec in "${FALLBACK_TORCH_VERSIONS[@]}"; do
        if try_install pip install --extra-index-url "${TORCH_CPU_INDEX}" "${spec}"; then
          echo "[ok] Installed ${spec} from CPU index"
          INSTALLED_TORCH=1
          break
        fi
      done
    fi
    if [[ "${INSTALLED_TORCH}" -eq 0 ]]; then
      echo "[fatal] Could not install torch with CPU wheels. Please check your Python version (${PY_MM}) or internet access."
      exit 1
    fi

    # Remove torch packages from requirements before installing the rest
    awk 'BEGIN{IGNORECASE=1} !/^(torch|torchvision|torchaudio)/ {print}' requirements.txt > /tmp/requirements.no-torch.txt
    pip install -r /tmp/requirements.no-torch.txt
  else
    # No torch in requirements; install all
    pip install -r requirements.txt
  fi
else
  # Minimal deps for this app
  pip install Flask gunicorn python-docx
fi

echo "[5/10] Sanity checks..."
python - <<'PY'
try:
    import flask, docx  # type: ignore
    print("Flask & python-docx OK")
except Exception as e:
    raise SystemExit(f"Dependency check failed: {e}")
PY

echo "[6/10] Ensuring runtime folders exist..."
mkdir -p generated/submissions generated

echo "[7/10] Killing any previous gunicorn/flask..."
pkill -f gunicorn 2>/dev/null || true
pkill -f "flask run" 2>/dev/null || true
sleep 0.3

echo "[8/10] Verifying app import path (${APP_MODULE})..."
python - <<PY
import importlib, sys
mod, _, appname = "${APP_MODULE}".partition(":")
m = importlib.import_module(mod)
if not hasattr(m, appname):
    raise SystemExit(f"App factory '{appname}' not found in module '{mod}'")
print("App import OK")
PY

echo "[9/10] Environment summary:"
echo "  VENV: ${VENV_DIR}"
echo "  PORT: ${PORT}"
echo "  WORKERS: ${WORKERS}"
echo "  APP_MODULE: ${APP_MODULE}"

echo "[10/10] Starting app with gunicorn -> ${APP_MODULE} on 0.0.0.0:${PORT} (workers=${WORKERS})"
exec gunicorn -w "${WORKERS}" -b "0.0.0.0:${PORT}" --reload "${APP_MODULE}"
