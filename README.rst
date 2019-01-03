Autorisations de circulation
============================

Application permettant la génération des courriers et des cartons d'autorisations de circulation dans le coeur du parc national du Mercantour.

Dans le cœur du parc, la circulation et le stationnement des véhicules motorisés (automobile, moto, cyclomoteur, etc.) sont interdits.
Cependant, chaque année le Parc national du Mercantour (PNM) délivre entre 600 et 800 autorisations individuelles de circuler au titre de l'article 15 du décret n° 2009-486 du 29 avril 2009.

Technologies
------------

* Langages : Python, HTML5, JS, CSS
* BDD : PostgreSQL, PostGIS
* Serveur : Debian 8 Jessie
* Framework PYTHON : Flask
* Framework JS : AngularJS
* Framework CSS : Bootstrap

Fonctionnalités
---------------

Consulter les fonctionnalités : A venir

License
-------

* Application développée par Kevin Samuel
* OpenSource - BSD
* Copyright © 2016 - Parc National du Mercantour

Installation
------------

Vous devez avoir ``git`` installé afin de pouvoir cloner le dépôt :

- sous Windows, utilisez ``cmder`` http://cmder.net/
- sous Mac, utilisez l'installeur officiel (https://sourceforge.net/projects/git-osx-installer/files/?SetFreedomCookie)
- sous Linux, ``git`` est téléchargeable dans les dépots (``sudo apt-get install git`` ou ``yum install git``)

Si l'installation est pour la production, on utilisera nginx, qu'il faut donc installer. Par exemple sous les distributions linux basées sur debian::

    sudo apt install nginx

Cette partie n'est pas obligatoire si on ne fait pas une mise en production.

Choisir un dossier où l'on va mettre le code de l'application. Sous Linux on utilise souvent /var/www (qui n'existe que si un serveur comme nginx a été installé au préalable)::

    cd /var/www

Tout autre dossier sur lequel vous avez les droits fera l'affaire si vous installez uniquement l'application pour le dev.

Ensuite, on récupère le code (si dans /var/www, il faudra les droits admins)
::

    git clone https://github.com/PnMercantour/autorisations_circulation auth_circu


Vous pouvez aussi télécharger une archive du dépôt et la dézipper :
::

    wget https://github.com/PnMercantour/autorisations_circulation/archive/master.zip


Ajouter un dossier pour l'upload. Toujours avec l'exemple de ubuntu, debian, mate, etc:

    sudo mkdir auth_circu/auth_circu/static/upload


Il faut avoir Python 3.6 installé :

- sous Windows on peut télécharger l'installer 64 bits sur le site officiel (https://www.python.org/downloads/release/python-360/)
- sous Mac on peut utiliser ``homebrew`` (http://docs.python-guide.org/en/latest/starting/install/osx/)
- si vous utilisez un système Linux récent comme la dernière version d'Ubuntu, vous pouvez utiliser les dépôts officiels. Ex: ``sudo apt-get install python3.6``
- Si vous utilisez un Linux plus ancien, il faut utiliser une source externe. Par exemple, sous Ubuntu, un ``ppa`` :

  ::

    sudo add-apt-repository ppa:fkrull/deadsnakes
    sudo apt update
    sudo apt-get install python3.6 python3.6-venv python3.6-dev

- sous Debian (jessie) en ``root``, on peut utiliser python:

  ::

    sudo apt-get install build-essential zlib1g-dev libbz2-dev libssl-dev libreadline-dev libncurses5-dev libsqlite3-dev libgdbm-dev libdb-dev libexpat-dev libpcap-dev liblzma-dev libpcre3-dev curl
    curl -kL https://raw.github.com/saghul/pythonz/master/pythonz-install | bash
    /usr/local/pythonz/bin/pythonz install 3.6.8
    ln -s $(pythonz locate 3.6.8) /usr/bin/python3.6

Il faut également ``virtualenv`` installé sur votre machine. Une installation récente de Python a généralement ``virtualenv`` pré-installé, soit sous la forme de la commande ``virtualenv``, soit sous la forme de la commande ``python -m venv``. Une exception notable sont les distributions Linux basées sur Debian (comme Ubuntu) qui ont besoin qu'on installe le package ``python3-virtualenv`` (``sudo apt-get install...``).

Faites attention à utiliser un ``virtualenv`` installé pour Python 3 et non Python 2.

On créé un environnement virtuel

::

    cd auth_circu
    python3.6 -m venv env
    source env/bin/activate # activer l'env

Si vous etes sous linux, assurez-vous d'avoir de quoi compiler les extensions C nécessaires à la connection à la base de données et à la génération des documents, particulièrement les headers ``Python`` et de ``libffi``, les libs de rendu ``cairo`` et ``pango`` ainsi qu'un compilateur comme ``GCC``.

Exemple sous Ubuntu ou debian :

::

    sudo apt-get install build-essential libffi-dev libcairo2 libpango1.0-0


On installe les dependances dans l'environnement virtuel :

::

    pip install -r requirements.txt

La génération de documents demande une version de développement de ``genshi``. Il faudra installer genshi à la main.

Exemple sous Ubuntu (avec le virtualenv activé):

::

    cd /tmp
    git clone https://github.com/edgewall/genshi.git
    cd genshi
    python setup.py install
    cd ..

Assurez-vous également que côté base de données :

- vous avez une version suffisament récente de PostgreSQL (9.5 ou plus).
- vous avez créez une base de données et un utilisateur (role) qui a tous les droits sur cette BDD.
- l'utilisateur a le droit de créer un schéma dans la base (même si le schéma existe déjà). Exemple en faisant : ``GRANT CREATE ON DATABASE nom_data_base TO nom_utilisateur``.
- la base de données est accessible de manière sécurisée depuis l'extérieur afin de permettre à UsersHub de se connecter.
- UsersHub possède les identifiants et I+ port de la base de données.

Exemple :

Installer PostGreSQL sur Jessie :

::

    sudo apt install postgresql-client-9.6 postgresql-9.6
    echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' >> /etc/apt/sources.list.d/postgresql.list
    wget --no-check-certificate -q https://www.postgresql.org/media/keys/ACCC4CF8.asc -O- | apt-key add -
    apt-get update
    apt install postgresql-9.6

Pour l'installation sous Mac, plusieurs procédures sont possibles: https://www.postgresql.org/download/macosx/

De même pour Windows: https://www.postgresql.org/download/windows/

Ensuite, créer une base de données ``auth_circu``, un utilisateur ``auth_circu`` et lui donner les droits sur la base.

Si vous êtes sur votre machine, utilisez une interface graphique type https://dbeaver.io.

Sur un serveur Linux, on peut le faire directement dans le shell de postgres:

::

    su postgres; cd
    createdb auth_circu
    createuser auth_circu
    psql
    ALTER USER "auth_circu" WITH PASSWORD 'mdp';
    GRANT ALL PRIVILEGES ON DATABASE "auth_circu" to auth_circu;
    \q
    exit

Remplacez ``'mdp'`` par le mot de passe de votre choix.


On génère ensuite un fichier de configuration. Lancer cette commande depuis le dossier "auth_circu" qui contient lui-même un dossier "auth_circu" :

::

    python -m auth_circu generate_config_file


Et répondez aux questions pour créer le fichier de config. Notez la commande affichera où elle a stockée le fichier de configuration. Garder ce chemin de fichier à portée de main.

Le fichier de configuration devrait ressembler à ceci :

::

    [security]
    database_uri = postgresql://nomutilisateur:motdepasse@host:port/nombasededonnees
    #exemple : database_uri = postgresql://auth_circu:mdp@127.0.0.1:5432/auth_circu
    secret_key = ga1CY.0mX[2Jcz@^+=#rPnB)"vAwr3~%QpY^Y]|=hn,!XBW(l0

Il permet de configurer la connexion à la base de données et fournir une clé secrète qui sécurise l'authentification de l'application. Ne partagez pas son contenu. Ne le rendez pas accessible. Ne le commitez pas sur git. Utilisez une autre clé secrète que celle-ci.

Il faut ensuite initialiser la base de données:

::

    # Création de la base et mise à zero de toutes les tables
    python -m auth_circu reset_db

    # optionnel mais recommandé: permet d'avoir des données pour les lieux
    # et les motifs des requêtes
    python -m auth_circu reset_restricted_places # données brutes, il y a des doublons: faire curation
    python -m auth_circu reset_motives

On peut également créer un utilisateur de test afin de pouvoir se logger:

::

    python -m auth_circu create_test_user <nom d'utilisateur> <mot de passe>

Néanmoins ceci ne fonctionnera qu'en mode dev. En production, les utilisateurs sont gérés par UsersHub.


Avant de poursuivre, on en cas d'erreur durant l'installation, vérifier les droits du dossier du projet.

Par exemple, pour donner les permissions au serveur d'accéder au code, sous une debian like avec nginx::

    # Le groupe du serveur est propriétaire du dossier
    # (optionnel, mais utile pour nginx en prod, sinon mettez votre utilisateur)
    sudo chown www-data:www-data -R auth_circu
    # S'assurer qu'on a les permissions de lecture et d'exécution au serveur
    sudo chmod 550 -R auth_circu
    # Donner accès en écriture au dossier d'upload
    sudo chmod ug+w auth_circu/auth_circu/static/upload

Si vous n'utilisez pas un serveur de production, remplacez l'utilisateur ``www-data`` par le votre.


Enfin, pour avoir les dates formatées dans la bonne langue, il faut générer les locales françaises installées sur son OS. Exemple sous les debian-like :

::

    sudo locale-gen fr_FR.UTF-8
    sudo update-locale


Lancer le serveur en mode dev
-------------------------------

Pour obtenir un serveur de dev (SANS les droits admin):

::

    runserver.py --config-file <chemin vers le fichier de config>


On peut passer les options ``--host 0.0.0.0`` pour écouter vers l'extérieur (utile si sur serveur distant) et ``--port`` si on souhaite changer le port (par défaut, 5000).

Vous pourrez alors accéder au service via ``http://<nom ou ip du server>:<port>``. Par exemple en local avec les valeurs par défaut: http://localhost:5000


Ce serveur n'est pas sécurisé ni performant, aussi ne l'utilisez pas pour un site en production.

Attention! Il n'existe pas d'outil pour passer du mode dev au mode prod: la base de données doit être remise à zero.


Lancer le serveur en mode prod
------------------------------

Pour mettre l'outil en production, il convient d'une part d'utiliser un serveur Web robuste, mais aussi de faire la liaison avec UsersHub pour les comptes utilisateurs.


Serveur Web
***********

N'importe quel serveur compatible WSGI fonctionnera. Nous allons ici utiliser un exemple avec le couple nginx/gunicorn.


D'abord, installer gunicorn dans le virtualenv (SANS les droits admin):

::

    pip install gunicorn


On peut démarrer le service à travers gunicorn en utilisant:

::

    <chemin vers gunicorn dans le virtualenv> auth_circu.wsgi:app -b <ip>:port --pid <chemin vers pid> -w <nombre de workers>

Exemple (SANS les droits admin):

::

    /var/www/auth_circu/env/bin/gunicorn auth_circu.wsgi:app -b 127.0.0.1:8000 --pid /tmp/auth_circu.pid -w 3

Mais pour s'assurer du lancement du service au démarrage, mieux vaut utiliser un gestionnaire d'init. La plupart des distributions linux modernes utilisent maintenant systemd, et nous utiliseront donc ce dernier comme exemple.

Créer un fichiern avec les droits admin, ``/etc/systemd/system/auth_circu.service`` contenant:

::


    [Unit]
    Description = auth_circu
    After = network.target

    [Service]
    PermissionsStartOnly = true
    PIDFile = /run/auth_circu/auth_circu.pid
    User = www-data
    Group = www-data
    WorkingDirectory = /var/www/auth_circu
    ExecStartPre = /bin/mkdir -p /run/auth_circu
    ExecStartPre = /bin/chown -R www-data:www-data /run/auth_circu
    ExecStart = <chemin vers gunicorn dans le virtualenv> auth_circu.wsgi:app -b 127.0.0.1:8000 --pid /run/auth_circu/auth_circu.pid -w 3
    ExecReload = /bin/kill -s HUP $MAINPID
    ExecStop = /bin/kill -s TERM $MAINPID
    ExecStopPost = /bin/rm -rf /run/auth_circu
    PrivateTmp = true

    [Install]
    WantedBy = multi-user.target

On signale à systemd de charger le service au démarrage:

::

    systemctl enable auth_circu.service


Et on démarre le service:

::

    systemctl start auth_circu.service

On peut vérifier le résultat avec:

::

    systemctl status auth_circu.service


Gunicorn installé, on peut maintenant mettre nginx en proxy.

Créer un fichier ``/etc/nginx/sites-available/auth_circu.conf`` contenant:

::

    upstream wsgi_server {
        server 127.0.0.1:8000; # gunicorn
    }

    server {
        listen 80;
        # exemple: server_name monserver.com;
        server_name <nom de domaine ou ip externe de votre serveur>;

        access_log /var/log/nginx/auth_circu_access.log ;
        error_log /var/log/nginx/auth_circu_error.log ;

        # On limite la taille de requêtes
        client_max_body_size 100M;

        # on sert les fichiers statiques directement
        location /static/ {
            # exemple: root /var/www/auth_circu/auth_circu/;
            root <chemin vers le dossier auth_circu contenant le dossier static>;
        }

        # On proxy tout le reste vers gunicorn
        location / {
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-Server $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            proxy_set_header Host $http_host;
            proxy_redirect off;
            proxy_pass http://wsgi_server;
            proxy_read_timeout 180s;
        }
    }

Puis faire un lien symbolique pour l'activer:

::

    ln -s /etc/nginx/sites-available/auth_circu.conf /etc/nginx/sites-enabled/auth_circu.conf


Redémarrer nginx pour prendre en compte la nouvelle configuration:

::

    service  nginx restart

Attention ! Certains anti-virus (e.g: certaines versions de Kaspersky) interceptent les documents générés par l'application et les altèrent à la volée au point de les rendre illisible. Si vous n'arrivez pas à lire vos documents, configurer nginx pour utiliser HTTPS, ce qui empêchera les anti-virus de lire le contenu des requêtes et de les modifier.

Liaison UsersHub
****************


Pour faire le lien avec UsersHub, qui s'occupera de gérer la partie authentification et droits d'accès, il faut donner accès à la base de données auth_circu à UsersHub.

Pour avoir accès à la base de donnée à l'extérieur et ce notamment pour se connecter au serveur UsersHub, modififier le fichier ``/etc/postgresql/<votre version de postgres>/main/pg_hba.conf`` et ajouter les IP des serveurs et des machines qui accèderont à la base de données ``auth_circu`` :

::

    host all all <ip de UsersHub> md5

Editer également le fichier ``/etc/postgresql/<votre version de postgres>/maim/postgresql.conf``  pour y décommenter ``listen_addresses = '*'``.

Puis redémarrer le service PostgreSQL :

::

    service postgresql restart


Vous pouvez maintenant faire le lien avec UsersHub, consultez la documentation de l'outil (https://usershub.readthedocs.io/fr/latest/index.html) ou contacter l'équipe de developpement pour le configurer pour se connecter à la base de auth_circu.

Attention, la base auth_circu ne doit pas contenir d'utilisateurs de test ou d'autorisation pour que cela marche. N'essayez donc pas de migrer une instance de dev vers la production, faites une installation depuis le début.


Données obligatoires
--------------------

Afin de générer les documents imprimables pour chaque autorisation, le service à besoin de deux données qu'il faut fournir manuellement:

- des templates de document  ``.odt`` à utiliser pour chaque type d'autorisation.
- une adresse de contact légal pour chaque utilisateur.

Les deux informations peuvent se fournir à travers l'admin accessible à travers le site. L'adresse de contact légal se tappe directement dans la partie "Contacts légaux" de l'admin, et sera intégrée automatiquement dans chaque autorisation.

Les templates doivent être uploadés via la partie "Modèles de document" de l'admin, et y être associé à un type d'autorisation. Chaque template sera utilisé comme modèle pour générer la version imprimable de l'autorisation. Le template est un document .odt ordinnaire mais qui accepte la syntaxe de template jinja à l'intérieur de tout champ de saisi afin de fabriquer le document dynamiquement à chaque téléchargement.

On peut y utiliser les variables suivantes:

- *auth_req*: l'objet AuthRequest en cours.
- *request_date*: la date de la requête, formatée en dd/mm/yy.
- *author_prefix*: M., Mme. ou vide.
- *feminin*: true si on doit utiliser le féminin.
- *auth_start_date*: la date de début d'autorisation, formatée en dd/mm/yy.
- *auth_end_date*: la date de fin d'autorisation, formatée en dd/mm/yy.
- *places_count*: le nombre de lieux concernés.
- *places*: une liste des objets RestrictedPlace concernés.
- *vehicules_count*: le nombre de véhicule concernés.
- *vehicules*: une liste des immatriculations de véhicules concernés.
- *legal_contact*: le texte designant le contact légal.
- *doc_creation_date*: la date de création du document, formatée en dd/mm/yy.

Le document étant de nature personnalisable, il n'est pas inclus à l'installation. Néanmoins le dossier "exemple/templates" du dépôt git contient des exemples de documents déjà utilisés en prod.
