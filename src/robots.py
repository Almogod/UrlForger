import urllib.robotparser

def get_robot_parser(domain):
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(domain.rstrip("/") + "/robots.txt")

    try:
        rp.read()
    except:
        return None

    return rp


def is_allowed(rp, url):
    if rp is None:
        return True
    return rp.can_fetch("*", url)
