from __future__ import print_function
import os
import sys
import subprocess
try:                                        # Older Pythons lack this
    import urllib.request                   # We'll let them reach the Python
    from importlib.util import find_spec    # check anyway
except ImportError:
    pass
import platform
import webbrowser
import hashlib
import argparse
import shutil
import stat
import time
try:
    import pip
except ImportError:
    pip = None

REQS_DIR = "lib"
sys.path.insert(0, REQS_DIR)
REQS_TXT = "requirements.txt"
REQS_NO_AUDIO_TXT = "requirements_no_audio.txt"
FFMPEG_BUILDS_URL = "https://ffmpeg.zeranoe.com/builds/"

INTRO = ("==========================\n"
         "Asimov - Discord Bot\n"
         "==========================\n")

IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"
IS_64BIT = platform.machine().endswith("64")
INTERACTIVE_MODE = not len(sys.argv) > 1  # CLI flags = non-interactive
PYTHON_OK = sys.version_info >= (3, 5)

FFMPEG_FILES = {
    "ffmpeg.exe"  : "e0d60f7c0d27ad9d7472ddf13e78dc89",
    "ffplay.exe"  : "d100abe8281cbcc3e6aebe550c675e09",
    "ffprobe.exe" : "0e84b782c0346a98434ed476e937764f"
}


def parse_cli_arguments():
    parser = argparse.ArgumentParser(description="Red - Discord Bot's launcher")
    parser.add_argument("--start", "-s",
                        help="Starts Red",
                        action="store_true")
    parser.add_argument("--auto-restart",
                        help="Autorestarts Red in case of issues",
                        action="store_true")
    parser.add_argument("--update-red",
                        help="Updates Red (git)",
                        action="store_true")
    parser.add_argument("--update-reqs",
                        help="Updates requirements (w/ audio)",
                        action="store_true")
    parser.add_argument("--update-reqs-no-audio",
                        help="Updates requirements (w/o audio)",
                        action="store_true")
    parser.add_argument("--repair",
                        help="Issues a git reset --hard",
                        action="store_true")
    return parser.parse_args()


def install_reqs(audio):
    remove_reqs_readonly()
    interpreter = sys.executable

    if interpreter is None:
        print("Python interpreter not found.")
        return

    txt = REQS_TXT if audio else REQS_NO_AUDIO_TXT

    args = [
        interpreter, "-m",
        "pip", "install",
        "--upgrade",
        "--target", REQS_DIR,
        "-r", txt
    ]

    if IS_MAC: # --target is a problem on Homebrew. See PR #552
        args.remove("--target")
        args.remove(REQS_DIR)

    code = subprocess.call(args)

    if code == 0:
        print("\nRéglages oppérés avec succès.")
    else:
        print("\nUne erreur à eu lieue lors de la configuration initiale.\n")


def update_pip():
    interpreter = sys.executable

    if interpreter is None:
        print("Python interpreter not found.")
        return

    args = [
        interpreter, "-m",
        "pip", "install",
        "--upgrade", "pip"
    ]

    code = subprocess.call(args)

    if code == 0:
        print("\nPip mis à jour.")
    else:
        print("\nUne erreur à eu lieue en mettant Pip à jour.")


def update_red():
    try:
        code = subprocess.call(("git", "pull", "--ff-only"))
    except FileNotFoundError:
        print("\nError: Git not found. It's either not installed or not in "
              "the PATH environment variable like requested in the guide.")
        return
    if code == 0:
        print("\nAsimov à été mis à jour.")
    else:
        print("\nAsimov n'a pas été correctement mis à jour.\nCela peut être causé par une modification du code source. Vous pouvez le réparer dans le menu Maintenance")


def reset_red(reqs=False, data=False, cogs=False, git_reset=False):
    if reqs:
        try:
            shutil.rmtree(REQS_DIR, onerror=remove_readonly)
            print("Paquets effacés.")
        except FileNotFoundError:
            pass
        except Exception as e:
            print("Une erreur à eu lieue: {}".format(e))
    if data:
        try:
            shutil.rmtree("data", onerror=remove_readonly)
            print("Fichier 'data' vidé.")
        except FileNotFoundError:
            pass
        except Exception as e:
            print("Une erreur à eu lieue: "
                  "{}".format(e))

    if cogs:
        try:
            shutil.rmtree("cogs", onerror=remove_readonly)
            print("Fichier 'cogs' vidé.")
        except FileNotFoundError:
            pass
        except Exception as e:
            print("Erreur lors du vidage: "
                  "{}".format(e))

    if git_reset:
        code = subprocess.call(("git", "reset", "--hard"))
        if code == 0:
            print("Asimov à été restoré.")
        else:
            print("La réparation à échouée.")


def download_ffmpeg(bitness):
    clear_screen()
    repo = "https://github.com/Twentysix26/Red-DiscordBot/raw/master/"
    verified = []

    if bitness == "32bit":
        print("Téléchargez s'il vous plait 'ffmpeg 32bit static' de la page qui "
              "va s'ouvrir.\nUne fois fait, ouvrez le dossier 'bin' se trouvant "
              "dans le zip.\nIl doit y avoir 3 fichiers: ffmpeg.exe, "
              "ffplay.exe, ffprobe.exe.\nMettez les dans le dossier où se trouve le launcher du bot.")
        time.sleep(4)
        webbrowser.open(FFMPEG_BUILDS_URL)
        return

    for filename in FFMPEG_FILES:
        if os.path.isfile(filename):
            print("{} déjà présent. Vérification de l'intégrité... "
                  "".format(filename), end="")
            _hash = calculate_md5(filename)
            if _hash == FFMPEG_FILES[filename]:
                verified.append(filename)
                print("Ok")
                continue
            else:
                print("Retéléchargement (erreur).")
        print("Téléchargement {}... Patientez.".format(filename))
        with urllib.request.urlopen(repo + filename) as data:
            with open(filename, "wb") as f:
                f.write(data.read())
        print("Téléchargement complet.")

    for filename, _hash in FFMPEG_FILES.items():
        if filename in verified:
            continue
        print("Vérification de {}... ".format(filename), end="")
        if not calculate_md5(filename) != _hash:
            print("Succès.")
        else:
            print("Les Hash ne correspondent pas, retéléchargez-le.")

    print("\nFichiers vérifiés avec succès.")


def verify_requirements():
    sys.path_importer_cache = {} # I don't know if the cache reset has any
    basic = find_spec("discord") # side effect. Without it, the lib folder
    audio = find_spec("nacl")    # wouldn't be seen if it didn't exist
    if not basic:                # when the launcher was started
        return None
    elif not audio:
        return False
    else:
        return True


def is_git_installed():
    try:
        subprocess.call(["git", "--version"], stdout=subprocess.DEVNULL,
                                              stdin =subprocess.DEVNULL,
                                              stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        return False
    else:
        return True


def requirements_menu():
    clear_screen()
    while True:
        print(INTRO)
        print("Minimum requis:\n")
        print("1. Installer la base + extension audio (Recommandé)")
        print("2. Installer la base seulement")
        if IS_WINDOWS:
            print("\nffmpeg (Audio):")
            print("3. Installer ffmpeg 32bit")
            if IS_64BIT:
                print("4. Installer ffmpeg 64bit (Pour windows 64 bits)")
        print("\n0. Retour")
        choice = user_choice()
        if choice == "1":
            install_reqs(audio=True)
            wait()
        elif choice == "2":
            install_reqs(audio=False)
            wait()
        elif choice == "3" and IS_WINDOWS:
            download_ffmpeg(bitness="32bit")
            wait()
        elif choice == "4" and (IS_WINDOWS and IS_64BIT):
            download_ffmpeg(bitness="64bit")
            wait()
        elif choice == "0":
            break
        clear_screen()


def update_menu():
    clear_screen()
    while True:
        print(INTRO)
        reqs = verify_requirements()
        if reqs is None:
            status = "Aucune base installée"
        elif reqs is False:
            status = "Base installée sans audio"
        else:
            status = "Base et audio installé"
        print("Status: " + status + "\n")
        print("MAJ:\n")
        print("Asimov:")
        print("1. Update Asimov + extensions basiques (recommandé)")
        print("2. Update Asimov")
        print("3. Update extensions basiques")
        print("\nAutres:")
        print("4. Update pip (Avec les droits d'administrateur)")
        print("\n0. Retour")
        choice = user_choice()
        if choice == "1":
            update_red()
            print("Mise à jour de extensions...")
            reqs = verify_requirements()
            if reqs is not None:
                install_reqs(audio=reqs)
            else:
                print("Les extensions n'ont pas étés installées.")
            wait()
        elif choice == "2":
            update_red()
            wait()
        elif choice == "3":
            reqs = verify_requirements()
            if reqs is not None:
                install_reqs(audio=reqs)
            else:
                print("Les extensions n'ont pas étés installées.")
            wait()
        elif choice == "4":
            update_pip()
            wait()
        elif choice == "0":
            break
        clear_screen()


def maintenance_menu():
    clear_screen()
    while True:
        print(INTRO)
        print("Maintenance:\n")
        print("1. Réparer Asimov (Retourne à une version basique sans endommager les données)")
        print("2. Supprimer dossier 'data' (Toutes les données sauvegardées)")
        print("3. Supprimer dossier 'lib' (Tous les modules et les paquets extérieurs)")
        print("4. Retour usine (Version totalement basique)")
        print("\n0. Retour")
        choice = user_choice()
        if choice == "1":
            print("Toutes les modifications personnelles sur le bot vont être effacées, êtes-vous certain ?")
            if user_pick_yes_no():
                reset_red(git_reset=True)
                wait()
        elif choice == "2":
            print("Toutes les données sur le bot vont être supprimées, êtes-vous certain ?")
            if user_pick_yes_no():
                reset_red(data=True)
                wait()
        elif choice == "3":
            reset_red(reqs=True)
            wait()
        elif choice == "4":
            print("Toutes les données sauvegardées et l'ensemble des modules rajoutés vont être supprimés. Êtes-vous certain ?")
            if user_pick_yes_no():
                reset_red(reqs=True, data=True, cogs=True, git_reset=True)
                wait()
        elif choice == "0":
            break
        clear_screen()


def run_red(autorestart):
    interpreter = sys.executable

    if interpreter is None: # This should never happen
        raise RuntimeError("Couldn't find Python's interpreter")

    if verify_requirements() is None:
        print("Il vous manque des paquets pour lancer Asimov.")
        if not INTERACTIVE_MODE:
            exit(1)

    cmd = (interpreter, "red.py")

    while True:
        try:
            code = subprocess.call(cmd)
        except KeyboardInterrupt:
            code = 0
            break
        else:
            if code == 0:
                break
            elif code == 26:
                print("Redémarrage de Asimov...")
                continue
            else:
                if not autorestart:
                    break

    print("Asimov arrêté. Exit code: %d" % code)

    if INTERACTIVE_MODE:
        wait()


def clear_screen():
    if IS_WINDOWS:
        os.system("cls")
    else:
        os.system("clear")


def wait():
    if INTERACTIVE_MODE:
        input("Appuyez sur Entrer pour continuer.")


def user_choice():
    return input("> ").lower().strip()


def user_pick_yes_no():
    choice = None
    yes = ("yes", "y")
    no = ("no", "n")
    while choice not in yes and choice not in no:
        choice = input("Yes/No > ").lower().strip()
    return choice in yes


def remove_readonly(func, path, excinfo):
    os.chmod(path, 0o755)
    func(path)


def remove_reqs_readonly():
    """Workaround for issue #569"""
    if not os.path.isdir(REQS_DIR):
        return
    os.chmod(REQS_DIR, 0o755)
    for root, dirs, files in os.walk(REQS_DIR):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o755)
        for f in files:
            os.chmod(os.path.join(root, f), 0o755)


def calculate_md5(filename):
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def create_fast_start_scripts():
    """Creates scripts for fast boot of Red without going
    through the launcher"""
    interpreter = sys.executable
    if not interpreter:
        return

    call = "\"{}\" launcher.py".format(interpreter)
    start_red = "{} --start".format(call)
    start_red_autorestart = "{} --start --auto-restart".format(call)
    modified = False

    if IS_WINDOWS:
        ccd = "pushd %~dp0\n"
        pause = "\npause"
        ext = ".bat"
    else:
        ccd = 'cd "$(dirname "$0")"\n'
        pause = "\nread -rsp $'Appuyez sur Entrer pour continuer...\\n'"
        if not IS_MAC:
            ext = ".sh"
        else:
            ext = ".command"

    start_red             = ccd + start_red             + pause
    start_red_autorestart = ccd + start_red_autorestart + pause

    files = {
        "start_red"             + ext : start_red,
        "start_red_autorestart" + ext : start_red_autorestart
    }

    if not IS_WINDOWS:
        files["start_launcher" + ext] = ccd + call

    for filename, content in files.items():
        if not os.path.isfile(filename):
            print("Creating {}... (fast start scripts)".format(filename))
            modified = True
            with open(filename, "w") as f:
                f.write(content)

    if not IS_WINDOWS and modified: # Let's make them executable on Unix
        for script in files:
            st = os.stat(script)
            os.chmod(script, st.st_mode | stat.S_IEXEC)


def main():
    print("Verification de l'installation...")
    has_git = is_git_installed()
    is_git_installation = os.path.isdir(".git")
    if IS_WINDOWS:
        os.system("TITLE Asimov Discord Bot - Launcher")
    clear_screen()

    try:
        create_fast_start_scripts()
    except Exception as e:
        print("Erreur lors de la création du fast script: {}\n".format(e))

    while True:
        print(INTRO)

        if not is_git_installation:
            print("ATTENTION : Asimov n'a pas été installé correctement, il manque Git."
                  "Veuillez s'il vous plait refaire l'installation")

        if not has_git:
            print("WARNING: Git not found. This means that it's either not "
                  "installed or not in the PATH environment variable like "
                  "requested in the guide.\n")

        print("1. Lancer Asimov avec autorestart")
        print("2. Lancer Asimov")
        print("3. Mettre à jour")
        print("4. Installer la base")
        print("5. Maintenance")
        print("\n0. Quitter")
        choice = user_choice()
        if choice == "1":
            run_red(autorestart=True)
        elif choice == "2":
            run_red(autorestart=False)
        elif choice == "3":
            update_menu()
        elif choice == "4":
            requirements_menu()
        elif choice == "5":
            maintenance_menu()
        elif choice == "0":
            break
        clear_screen()

args = parse_cli_arguments()

if __name__ == '__main__':
    abspath = os.path.abspath(__file__)
    dirname = os.path.dirname(abspath)
    # Sets current directory to the script's
    os.chdir(dirname)
    if not PYTHON_OK:
        print("Red needs Python 3.5 or superior. Install the required "
              "version.\nPress enter to continue.")
        if INTERACTIVE_MODE:
            wait()
        exit(1)
    if pip is None:
        print("Red cannot work without the pip module. Please make sure to "
              "install Python without unchecking any option during the setup")
        wait()
        exit(1)
    if args.repair:
        reset_red(git_reset=True)
    if args.update_red:
        update_red()
    if args.update_reqs:
        install_reqs(audio=True)
    elif args.update_reqs_no_audio:
        install_reqs(audio=False)
    if INTERACTIVE_MODE:
        main()
    elif args.start:
        print("Starting Red...")
        run_red(autorestart=args.auto_restart)
