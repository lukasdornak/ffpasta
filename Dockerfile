FROM lukasdornak/djuwinx:1.0

COPY . /app/
COPY admin/forms.py /usr/local/lib/python3.7/site-packages/django/contrib/admin/forms.py
COPY auth/admin.py /usr/local/lib/python3.7/site-packages/django/contrib/auth/admin.py
COPY auth/forms.py /usr/local/lib/python3.7/site-packages/django/contrib/auth/forms.py
COPY auth/models.py /usr/local/lib/python3.7/site-packages/django/contrib/auth/models.py
COPY auth/management/__init__.py /usr/local/lib/python3.7/site-packages/django/contrib/auth/management/__init__.py

ENV DJANGO_SETTINGS_MODULE=settings

RUN apk add --update --upgrade --no-cache \
        cairo-dev \
        pango-dev \
        gdk-pixbuf \
        jpeg-dev; \
    apk add --update --no-cache --virtual .build-deps \
		build-base \
		musl-dev \
		zlib-dev \
		libffi-dev \
		gdk-pixbuf-dev; \
	pip3 install --no-cache-dir -r /app/requirements.txt; \
	apk del .build-deps

RUN django-admin collectstatic --noinput\
    && mkdir /app/data \
    && mkdir /app/media \
    && chown nginx /app/data \
    && chown nginx /app/media

ENTRYPOINT uwsgi --ini /etc/uwsgi/djuwinx_uwsgi.ini && nginx && /bin/ash