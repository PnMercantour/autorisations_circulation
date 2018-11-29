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

Ensuite, on récupère le code
::

    git clone https://github.com/PnMercantour/autorisations_circulation auth_circu

Vous pouvez aussi télécharger une archive du dépôt et la dézipper : 
::

    wget https://github.com/PnMercantour/autorisations_circulation/archive/master.zip

Il faut avoir Python 3.6 installé :

- sous Windows on peut télécharger l'installer 64 bits sur le site officiel (https://www.python.org/downloads/release/python-360/)
- sous Mac on peut utiliser ``homebrew`` (http://docs.python-guide.org/en/latest/starting/install/osx/)
- si vous utilisez un système Linux récent comme la dernière version d'Ubuntu, vous pouvez utiliser les dépôts officiels. Ex: ``sudo apt-get install python3.6``
- Si vous utilisez un Linux plus ancien, il faut utiliser une source externe. Par exemple, sous Ubuntu, un ``ppa`` :

  ::

    sudo add-apt-repository ppa:fkrull/deadsnakes
    sudo apt update
    sudo apt-get install python3.6 python3.6-venv python3.6-dev

- sous Debian (jessie) en ``root`` :

  ::

    vi /etc/apt/sources.list
		
Ajouter à la fin du fichier : ``deb http://ftp.de.debian.org/debian testing main`` puis : 

::

  echo 'APT::Default-Release "jessie-updates";' | tee -a /etc/apt/apt.conf.d/00local
  apt-get update
  apt-get -t testing install python3.6 python3.6-venv python3.6-dev
  python3.6 -V


Il faut également ``virtualenv`` installé sur votre machine. Une installation récente de Python a généralement ``virtualenv`` pré-installé, soit sous la forme de la commande ``virtualenv``, soit sous la forme de la commande ``python -m venv``. Une exception notable sont les distributions Linux basées sur Debian (comme Ubuntu) qui ont besoin qu'on installe le package ``python3-virtualenv`` (``sudo apt-get install...``).

Faites attention à utiliser un ``virtualenv`` installé pour Python 3 et non Python 2.

On créé un environnement virtuel

::

    cd auth_circu
    python3.6 -m venv env  
    source env/bin/activate # activer l'env
    
Assurez-vous d'avoir de quoi compiler les extensions C nécessaires à la connection à la base de données et à la génération des documents, particulièrement les headers ``Python`` et de ``libffi``, les libs de rendu ``cairo`` et ``pango`` ainsi qu'un compilateur comme ``GCC``. 

Exemple sous Ubuntu :

::

    sudo apt-get install build-essential libffi-dev libcairo2 libpango1.0-0

On installe les dependances dans l'environnement virtuel :

::

    pip install -r requirements.txt
    
La génération de documents demande une version de développement de ``genshi``. Il faudra installer genshi à la main.

Exemple sous Ubuntu :

::

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

Exemple : Installer PostGreSQL sur Jessie :

::

    apt install postgresql-9.6
    service postgresql start
    su postgres
    createdb auth_circu
    createuser auth_circu
    psql
    ALTER USER "auth_circu" WITH PASSWORD 'mdp';
    GRANT ALL PRIVILEGES ON DATABASE "auth_circu" to auth_circu;
    \q 
    exit

Configurer PostgreSQL pour avoir accès à la base de donnée à l'extérieur et ce notamment pour se connecter au serveur UsersHub :

::

    /etc/postgresql/9.6/main# nano pg_hba.conf

Ajouter les IP des serveurs et des machines qui accèderont à la base de données ``auth_circu`` :

::

    host all all "IP_addresses" md5

Configurer également le fichier ``/etc/postgresql/9.6/main# nano postgresql.conf`` :

# - Connection Settings -

Décommenter ``listen_addresses = '*'``

Puis redémarrer le service PostgreSQL :

::

    service postgresql restart

On génère un fichier de configuration. Lancer cette commande depuis le dossier qui contient le dossier "auth_circu" :

::

    python -m auth_circu generate_config_file

Le fichier de configuration devrait ressembler à ceci :

::

    [security]
    database_uri = postgresql://nomutilisateur:motdepasse@host:port/nombasededonnees
    #exemple : database_uri = postgresql://auth_circu:mdp@127.0.0.1:5432/auth_circu   
    secret_key = ga1CY.0mX[2Jcz@^+=#rPnB)"vAwr3~%QpY^Y]|=hn,!XBW(l0

Il permet de configurer la connexion à la base de données et fournir une clé secrète qui sécurise l'authentification de l'application. Ne partagez pas son contenu. Ne le rendez pas accessible. Ne le commitez pas sur git. Utilisez une autre clé secrète que celle-ci.

Afin d'avoir les dates formatées dans la bonne langue, il faut générer les locales françaises installées sur son OS. Exemple sous Debian :

::

    sudo locale-gen fr_FR.UTF-8
    sudo update-locale 

Un server WSGI pour lancer le site Web flask est indispensable. Gunicorn ou uWSGI étant les standards.

Dans l'environnement virtuel :

::

    pip install gunicorn

Installer la base de donnée

::

    python -m auth_circu reset_db
