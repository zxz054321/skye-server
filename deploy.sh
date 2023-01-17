if ! pip show coscmd &>/dev/null; then
  pip install coscmd
fi

chmod 777 scf_bootstrap gunicornbin
mkdir dist || rm dist/skye_server.zip
mv .env .env.tmp
mv .env.scf .env
zip -r dist/skye_server.zip \
  "skye/" \
  "skye_server/" \
  ".env" \
  "gunicornbin" \
  "manage.py" \
  "requirements.txt" \
  "scf_bootstrap" \
  "scf_console.sh" \
  -x "*/__pycache__/*"

mv .env .env.scf
mv .env.tmp .env

# upload server src
coscmd --bucket "skye-src-1251045573" --config_path ".cos.conf" --log_path "cos.log" upload \
  --sync \
  "dist/skye_server.zip" \
  "/server.zip"
coscmd --bucket "skye-src-1251045573" --config_path ".cos.conf" --log_path "cos.log" upload \
  --sync \
  "scf_layer.zip" \
  "/layer.zip"

# upload admin static assets
python manage.py collectstatic --no-input --link
coscmd --bucket "skye-1251045573" --config_path ".cos.conf" --log_path "cos.log" upload \
  --recursive \
  --sync \
  --force \
  --delete \
  "dist/static/admin" \
  "/admin"
