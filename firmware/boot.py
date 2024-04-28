
import storage

# Mount the filesystem in read-write mode so you can store configuration
storage.remount("/", readonly=False)
