# Autorisations de circulation

Application permettant la génération des courriers et des cartons d'autorisations de circulation dans le coeur du parc national du Mercantour.

Dans le cœur du parc, la circulation et le stationnement des véhicules motorisés (automobile, moto, cyclomoteur, etc.) sont interdits.
Cependant, chaque année le Parc national du Mercantour (PNM) délivre entre 600 et 800 autorisations individuelles de circuler au titre de l'article 15 du décret n° 2009-486 du 29 avril 2009.

# Technologies

* Langages : Python, HTML5, JS, CSS
* BDD : PostgreSQL, PostGIS
* Serveur : Debian 8 Jessie
* Framework PYTHON : Flask
* Framework JS : AngularJS
* Framework CSS : Bootstrap

# Fonctionnalités

Consulter les fonctionnalités : A venir

# Installation

Consulter la documentation : A venir

# License

* Application développée par Kevin Samuel
* OpenSource - BSD
* Copyright © 2016 - Parc National du Mercantour

# Installation

Il faut avoir Python 3.6 desinstallé:

- sous windows on peut télécharger l'installer 64bits sur le site officiel (https://www.python.org/downloads/release/python-360/)
- sous mac on peut utiliser homebrew (http://docs.python-guide.org/en/latest/starting/install/osx/)
- if vous utilisez un système linux récent comme la dernière version d'Ubuntu, vous pouvez utiliser les repositories officiels. Ex: sudo apt-get install python3.6
- Si vous utilisez un linux plus anciens, il faut utiliser une source externe. Par exemple, sous Ubuntu, un ppa:
    * sudo add-apt-repository ppa:fkrull/deadsnakes  
    * sudo apt update  
    * sudo apt-get install python3.6
- sinon vous pouvez utiliser pythonz (https://github.com/saghul/pythonz)

Vous devez avoir git installté afin de pouvoir cloner le repository :

- sous windows, utilisez cmder http://cmder.net/
- sous mac, utilisez l'installeur officiel (https://sourceforge.net/projects/git-osx-installer/files/?SetFreedomCookie)
- sous linux, git est dans les dépots (sudo apt-get install git or yum install git)

Ensuite, on récupère le code::

    git clone https://github.com/PnMercantour/autorisations_circulation auth_circu

Il faut également virtualenv installé sur votre machine. Une installation récente de Python a généralement virtualenv pré-installé, soit sous la forme de la commande virtualenv, soit sous la forme de la commande python -m venv. Une exception notable sont les distributions linux basées sur debian (comme Ubuntu) qui ont besoin qu'on installe le package python3-virtualenv (sudo apt-get install...).

Faites attention à utiliser un virtualenv installé pour Python 3 et non Python 2. 

On créé un environnement virtuel::

    cd auth_circu
    virtualenv env -p /chemin/vers/python3.6 # creer l'environnement virtuel
    source env/bin/activate # activer l'env

On installe les dependances dans l'environnement virtuel::

    pip install -r requirements.txt 
    
On génère un fichier de configuration::

    python -m autcircu generate_config_file
    
Le fichier de configuration devrait ressembler à ceci:

    [security]
    database_uri = postgresql://nomutilisateur:motdepasse@host:port/nombasededonnees
    secret_key = ga1CY.0mX[2Jcz@^+=#rPnB)"vAwr3~%QpY^Y]|=hn,!XBW(l0
    
 Il permett de configurer la connexion à la base de données et fournir une clé secrète qui sécurise l'authentification de l'application. Ne partagez pas son contenu. Ne le rendez pas accessible. Ne le commitez pas sur git.
 
Assurez-vous également que côté base de données:

- vous avez une version suffisament récente de postgres (9.5 ou plus)
- l'utilisateur a le droit de créer un schéma dans la base (même si le schéma existe déjà). Exemple en faisant: GRANT CREATE ON DATABASE nom_data_base TO nom_utilisateur;

