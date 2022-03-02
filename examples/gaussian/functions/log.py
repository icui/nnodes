import os


def write_status(outdir, message):

    print(message)
    fname = "STATUS.txt"
    file = os.path.join(outdir, fname)

    with open(file, "w") as f:
        f.write(message)


def write_log(outdir, message):
    fname = "LOG.txt"
    file = os.path.join(outdir, fname)

    with open(file, "a") as f:
        f.write(message + "\n")


def clear_log(outdir):
    fname = "LOG.txt"
    file = os.path.join(outdir, fname)

    with open(file, "w") as f:
        f.close()
