from tkinter import *
from tkinter import filedialog
from functools import partial
from tkinter.ttk import Progressbar

import Klient as k
import socket
import ntpath
from os import listdir, makedirs
from os.path import isfile, join, isdir, splitext
import os

def send(my_msg, msg_list, connection, file,  event=KeyboardInterrupt):
    msg = my_msg.get()
    my_msg.set("")

    if msg != '':

        if (msg == file.name):
            if (file.size > file.min & file.size < file.max):
                msg_list.insert(END, "sending file " + file.name)
                msg_list.select_clear(msg_list.size() - 2)
                msg_list.select_set(END)
                msg_list.yview(END)
                k.SecureConnector.sendFile(connection, file)
                msg_list.insert(END, "cannot send messages while sending file")
                msg_list.select_clear(msg_list.size() - 2)
                msg_list.select_set(END)
                msg_list.yview(END)
            elif (file.size > file.max):
                msg_list.insert(END, "file " + file.name + " is too big. Max 100MB")
                msg_list.select_clear(msg_list.size() - 2)
                msg_list.select_set(END)
                msg_list.yview(END)
        else:
            k.SecureConnector.sendMessage(connection, msg)
            msg_list.insert(END, "ME: " + msg)
            msg_list.select_clear(msg_list.size() - 2)
            msg_list.select_set(END)
            msg_list.yview(END)

class Window:
    def recive(self, msg):
        if (msg.split('=', maxsplit=1))[0] == "progress_bar:":
            self.progress['value'] = int((msg.split('=', maxsplit=1))[1])
            if self.progress['value'] == 100:
                self.msg_list.insert(END, "finished sending file")
                self.msg_list.select_clear(self.msg_list.size() - 2)
                self.msg_list.select_set(END)
                self.msg_list.yview(END)
        else:
            self.msg_list.insert(END, msg)
            self.msg_list.select_clear(self.msg_list.size() - 2)
            self.msg_list.select_set(END)
            self.msg_list.yview(END)

    def __del__(self):
        self.connection.close()
        self.window.destroy()

    def __init__(self):
        self.loggin()

    def loggin(self):
        popup = Tk()
        name = StringVar()
        passoword = StringVar()
        ip = StringVar()
        port = StringVar()
        popup.wm_title("Logging")
        label = Label(popup, text="Your name")
        label.grid(row=0, column=0)
        entryName = Entry(popup, textvariable=name)
        entryName.grid(row=0, column=1, padx=20)
        label2 = Label(popup, text="Password")
        label2.grid(row=1, column=0)
        passw = Entry(popup, textvariable=passoword)
        passw.grid(row=1, column=1)
        label3 = Label(popup, text="Your ip")
        label3.grid(row=2, column=0)
        ipentry = Entry(popup, textvariable=ip)
        ipentry.grid(row=2, column=1)
        label4 = Label(popup, text="Your port")
        label4.grid(row=3, column=0)
        portt = Entry(popup, textvariable=port)
        portt.grid(row=3, column=1)
        B1 = Button(popup, text="Login", command=lambda: self.createWindow(popup, entryName, passw, ip, port))
        B1.grid(row=4, column=1)
        popup.mainloop()

    def createWindow(self, popup, name, password, ip, port):
        # Creating window and frames, setting title
        self.name = name.get()
        self.password = password.get()
        self.port = port.get()
        self.ip = ip.get()
        popup.destroy()
        # do zapisania hasło
        self.window = root = Tk()

        self.window.title("Pierwszy projekt BSK")
        messages_frame = Frame(self.window)
        friends_frame = Frame(self.window)
        self.file = k.File()
        self.connection = k.SecureConnector(self.password, self.ip, self.port)
        self.createLabel()
        self.createMenu(friends_frame)
        self.createMessageFrame(messages_frame)
        self.bindConnector()
        self.createFriends(friends_frame)
        self.window.mainloop()

    def createLabel(self):
        self.mode = StringVar(self.window)
        self.mode.set("ECB")
        self.label = Label(self.window, textvariable=self.mode).pack()

    def createMenu(self, friends_frame):
        self.menuBar = Menu(self.window)
        mode = Menu(self.menuBar, tearoff=0)
        contacts = Menu(self.menuBar, tearoff=0)

        xecb = partial(self.changeMode, "ECB")
        mode.add_command(label="ECB", command=xecb)

        xcbc = partial(self.changeMode, "CBC")
        mode.add_command(label="CBC", command=xcbc)

        xcfc = partial(self.changeMode, "CFB")
        mode.add_command(label="CFB", command=xcfc)

        xofb = partial(self.changeMode, "OFB")
        mode.add_command(label="OFB", command=xofb)

        contacts.add_command(label="Add contact", command=self.addContact)
        contacts.add_command(label="Edit contact")
        contacts.add_command(label="Delete contact")
        contacts.add_command(label="Refresh", command=lambda: self.refresh(friends_frame))

        self.menuBar.add_cascade(label="Mode", menu=mode)
        self.menuBar.add_cascade(label="Contacts", menu=contacts)
        self.window.config(menu=self.menuBar)

    def addContact(self):
        popup = Tk()
        name = StringVar()
        ip = StringVar()
        port = StringVar()
        popup.wm_title("Adding contact")

        label = Label(popup, text="Name of the contact")
        label.grid(row=0, column=0)
        entryName = Entry(popup, textvariable=name)
        entryName.grid(row=0, column=1, padx=20)

        label2 = Label(popup, text="IP address")
        label2.grid(row=1, column=0)
        ipAddress = Entry(popup, textvariable=ip)
        ipAddress.grid(row=1, column=1)

        label3 = Label(popup, text="Port")
        label3.grid(row=2, column=0)
        portEntry = Entry(popup, textvariable=port)
        portEntry.grid(row=2, column=1)

        # save = partial(self.saveContact, name, ip, popup)
        B1 = Button(popup, text="Save", command=lambda: self.saveContact(entryName, ipAddress, portEntry, popup))
        B1.grid(row=3, column=1)
        popup.mainloop()

    def saveContact(self, name, ip, portEntry, popup):
        n = name.get()
        i = ip.get()
        p = portEntry.get()
        self.contacts.append((n, i, p))
        file = open(join('./saves', n + '.txt'), 'w+')
        file.write(i + '\n' + p)
        file.close()
        popup.destroy()

    def createMessageFrame(self, messages_frame):
        entry_frame = Frame(messages_frame)
        progress_frame = Frame(messages_frame)
        progress_frame.pack(side=TOP, fill=BOTH)
        # Creating window components
        self.my_msg = StringVar()
        self.scrollbar = Scrollbar(messages_frame)
        self.msg_list = Listbox(messages_frame, height=15, width=50, yscrollcommand=self.scrollbar.set)
        self.entry_field = Entry(entry_frame, textvariable=self.my_msg, width=35)
        self.window.protocol("WM_DELETE_WINDOW", self.__del__)

        # Setting message list and scrollbar in a window
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.progress = Progressbar(progress_frame, orient=HORIZONTAL,
                               length=100, mode='determinate')
        self.progress.pack(side=TOP, fill=BOTH)
        self.msg_list.pack(side=TOP, fill=BOTH)
        self.msg_list.pack()


        # Configurate message list and scrollbar
        self.msg_list.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.msg_list.yview)

        # Creating send button and biding it with a function


        self.entry_field.pack(fill=X, padx=15, side=LEFT)
        self.send_button = Button(entry_frame, text="Send",
                                  command=lambda: send(self.my_msg, self.msg_list, self.connection, self.file))
        self.file_button = Button(entry_frame, text="Browse a file", command=self.fileDialog)
        self.send_button.pack(side=LEFT)
        self.file_button.pack(side=LEFT)
        entry_frame.pack(side=BOTTOM)
        messages_frame.pack(side=LEFT)

    def fileDialog(self):
        filePath = filedialog.askopenfilename(initialdir="/", title="Select a file",
                                              filetypes=(("all files", "*.*"), ("jpeg files", "*.jpg")))
        self.my_msg.set(ntpath.basename(filePath))
        self.file.path = filePath
        self.file.name = ntpath.basename(filePath)
        self.file.size = os.stat(filePath).st_size
        # print(self.file.size)

    def bindConnector(self):
        addMessage = partial(send, self.my_msg, self.msg_list, self.connection, self.file)
        self.entry_field.bind("<Return>", addMessage)
        self.connection.bind_to(self.recive)

    def changeMode(self, mode):
        self.mode.set(mode)
        self.connection.changeMode(mode)

    def createFriends(self, friends_frame):
        path = './saves'
        if not isdir(path):
            makedirs(path)
        onlyFiles = [f for f in listdir(path) if isfile(join(path, f))]

        self.contacts = list()
        self.buttons = list()
        for index, contact in enumerate(onlyFiles):
            f = open(join(path, contact), 'r')
            elements = f.readlines()
            self.contacts.append((splitext(contact)[0],
                             elements[0].rstrip(), elements[1]))
            connect = partial(self.connect, contact)
            button = Button(friends_frame, text=(splitext(contact)[0]), command=connect)
            self.buttons.append(button)
            button.pack()
            f.close()
        friends_frame.pack(side=RIGHT)
        return len(onlyFiles)

    def refresh(self, friends_frame):
        self.contacts.clear()
        for button in self.buttons:
            button.destroy()
            self.buttons.remove(button)
        self.buttons[0].destroy()
        self.buttons.clear()
        self.createFriends(friends_frame)

    def connect(self, name):
        path = './saves/' + str(name)
        file = open(path, 'r')
        elements = file.readlines()
        elements[0] = elements[0].rstrip()
        self.connection.close()
        self.connection.chost = elements[0]
        self.connection.cport = int(elements[1])
        self.connection.createClient()
        # self.connect #ip -> x[0], port -> elements[1]
        # print(x[0])


