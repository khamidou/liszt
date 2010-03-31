# liszt_util.py - classes used both by liszt and liszt-daemon.

import os, sys
import urllib, urllib2, cookielib
from urllib import quote
from urllib2 import HTTPError, URLError
import time
from dateutil.parser import parse as parse_date
import atexit
from signal import SIGTERM 

try:
    import json 
except ImportError:
    import simplejson as json                                                                                                                         

base = "http://www.todoliszt.com/api/v1"

def bailout(msg):
    print msg
    return

def sorted_dirlist(path):
    def sortbyctime(a, b):
        da = parse_date(a)
        db = parse_date(b)
        if (da > db):
        	return 1
        elif da == db:
            	return 0
        else:
            	return -1

    return sorted(os.listdir(path), cmp=sortbyctime)


# The Daemon class comes from http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
class Daemon:
	"""
	A generic daemon class.
	
	Usage: subclass the Daemon class and override the run() method
	"""
	def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
		self.stdin = stdin
		self.stdout = stdout
		self.stderr = stderr
		self.pidfile = pidfile
	
	def daemonize(self):
		"""
		do the UNIX double-fork magic, see Stevens' "Advanced 
		Programming in the UNIX Environment" for details (ISBN 0201563177)
		http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
		"""
		try: 
			pid = os.fork() 
			if pid > 0:
				# exit first parent
				sys.exit(0) 
		except OSError, e: 
			sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
			sys.exit(1)
	
		# do second fork
		try: 
			pid = os.fork() 
			if pid > 0:
				# exit from second parent
				sys.exit(0) 
		except OSError, e: 
			sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
			sys.exit(1) 
	
		# redirect standard file descriptors
		sys.stdout.flush()
		sys.stderr.flush()
		si = file(self.stdin, 'r')
		so = file(self.stdout, 'a+')
		se = file(self.stderr, 'a+', 0)
		os.dup2(si.fileno(), sys.stdin.fileno())
		os.dup2(so.fileno(), sys.stdout.fileno())
		os.dup2(se.fileno(), sys.stderr.fileno())
	
		# write pidfile
		atexit.register(self.delpid)
		pid = str(os.getpid())
		file(self.pidfile,'w+').write("%s\n" % pid)
	
	def delpid(self):
		os.remove(self.pidfile)

	def start(self):
		"""
		Start the daemon
		"""
		# Check for a pidfile to see if the daemon already runs
		try:
			pf = file(self.pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None
	
		if pid:
                    	# Exit silently
			sys.exit(1)
		
		# Start the daemon
		self.daemonize()
		self.run()

	def stop(self):
		"""
		Stop the daemon
		"""
		# Get the pid from the pidfile
		try:
			pf = file(self.pidfile,'r')
			pid = int(pf.read().strip())
			pf.close()
		except IOError:
			pid = None
	
		if not pid:
			message = "pidfile %s does not exist. Daemon not running?\n"
			sys.stderr.write(message % self.pidfile)
			return # not an error in a restart

		# Try killing the daemon process	
		try:
			while 1:
				os.kill(pid, SIGTERM)
				time.sleep(0.1)
		except OSError, err:
			err = str(err)
			if err.find("No such process") > 0:
				if os.path.exists(self.pidfile):
					os.remove(self.pidfile)
			else:
				print str(err)
				sys.exit(1)

	def restart(self):
		"""
		Restart the daemon
		"""
		self.stop()
		self.start()

	def run(self):
		"""
		You should override this method when you subclass Daemon. It will be called after the process has been
		daemonized by start() or restart().
		"""
                pass


class LisztSession:
    def __init__(self):

        self.jar = cookielib.LWPCookieJar()
        if os.path.isfile(os.path.expanduser('~/.liszt/cookiejar')):
            self.jar.load(os.path.expanduser('~/.liszt/cookiejar'))

        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.jar))
        urllib2.install_opener(self.opener)

    def login(self, username, password):
        d = {'username' : username, 'password': password}
        ed = urllib.urlencode(d)
        
        while True:
            try:
                urllib2.urlopen(base + "/login/", ed)
                return
            except URLError, http_error:
                print "Unable to log you in - http error code " + str(http_error.code)
                time.sleep(5 * 60) # Try to reconnect every five minutes.
                continue

    def create_list(self, listname):
        try:
            urllib2.urlopen(base + "/create/" + quote(listname.encode("utf8")) + "/")
        except HTTPError:
            bailout("Unable to create the list " + listname)

    def create_list_entry(self, listname, entry):
        try:
            urllib2.urlopen(base + "/create/" + quote(listname) + "/" + quote(entry) + "/")
        except HTTPError:
            bailout("Unable to create the list entry in list " + listname)

    def get_lists_list(self):
        try:
            req = urllib2.urlopen(base + "/getlists/")
        except HTTPError:
            bailout("Unable to get a list of the available lists")
            
        return json.load(req)

    def get_list(self, listname):
        req = None
        print type(listname)
        listname = listname.encode("utf8")

        try:
            req = urllib2.urlopen(base + "/get/" + quote(listname) + "/")
        except URLError:
            bailout("Unable to open the list " + listname)
            sys.exit(-1)

        return json.load(req)

    def get_entry(self, listname, index):
        listname = listname.encode("utf8")

        try:
            req = urllib2.urlopen(base + "/get/" + quote(listname) + "/" + str(index) + "/")
        except HTTPError:
            bailout("Unable to get entry " + str(index) + " from list " + listname)
            return

        return json.load(req)

    def remove_list(self, listname):
        listname = listname.encode("utf8")

        try:
            urllib2.urlopen(base + "/remove/" + quote(listname) + "/")
        except HTTPError:
            bailout("Unable to remove the list " + listname)

    def remove_list_entry(self, listname, index):
        listname = listname.encode("utf8")

        try:
            urllib2.urlopen(base + "/remove/" + quote(listname) + "/" + quote(index) + "/")
        except HTTPError:
            bailout("Unable to remove the entry " + index + "from list " + listname)

    def update_list_entry(self, listname, index, contents):
        listname = listname.encode("utf8")
        ec = urllib.urlencode(contents)
        try:
            urllib2.urlopen(base + "/update/" + listname + "/" + str(index) + "/", ec)
        except HTTPError:
            bailout("Unable to update the list entry")

# Cached list manages a list cached on the client.
class CachedList(object):
    def __init__(self, listname):
        try:
            self.listname = listname
            fd = open(os.path.expanduser('~/.liszt/cached/') + listname)
            try:
                self.cached_list = json.load(fd)
            except ValueError:
            # Create it.
                try:
                    fd = open(os.path.expanduser('~/.liszt/cached/') + listname, 'w+')
                except IOError:
                    bailout("IOError when trying to create a cached list.")
            
                self.cached_list = {"name" : listname, "contents" : []}
                

        except IOError:
            # Create it.
            try:
                fd = open(os.path.expanduser('~/.liszt/cached/') + listname, 'w+')
            except IOError:
                bailout("IOError when trying to create a cached list.")
            
            self.cached_list = {"name" : listname, "contents" : []}

    def save(self):
        fd = open(os.path.expanduser('~/.liszt/cached/') + self.listname, 'w+')
        json.dump(self.cached_list, fd, encoding="utf8")

    def remove(self):
        os.unlink(os.path.expanduser('~/.liszt/cached/') + self.listname)

    def fget(self):
        return self.cached_list
    
    def fset(self, list):
        self.cached_list = list

    def fdel(self):
        del self.cached_list
        
    contents = property(fget, fset, fdel)
