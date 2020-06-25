import socket
from tkinter import *
import threaded
from Cryptodome import Random
import os
import os.path
import Window as W
import Cryptodome.Cipher.PKCS1_v1_5 as PKCS
import Cryptodome.Cipher.AES as AES
import Cryptodome.PublicKey.RSA as RSA
import Cryptodome.Hash.SHA256 as SHA256
from Cryptodome.Util.Padding import pad, unpad
from queue import SimpleQueue as fifo
from time import sleep as sleep

class File:
    def __init__(self):
        self.inFile = object
        self.outFile = object
        self.path = ''
        self.name = ''
        self.receiving = False
        self.sending = False
        self.size = 0
        self.min = 1000 #KB
        self.max = 1000000 #100MB
        self.currentSize = 0

class  SecureConnector:

    def __init__(self, password, ip, port):
        self.hasKey = False
        self.key = os.urandom(16)
        self.dKey = self.key
        self.mode = AES.MODE_ECB
        self.cipher = AES.new(self.key, self.mode)
        h = SHA256.new()
        h.update(bytes(password, encoding='utf8'))
        hash = h.hexdigest()
        #hash = pad(bytes(hash, encoding='utf8'), 256, style='iso7816')
        hash = bytes(hash, encoding='utf8')[:16]
        if os.path.isfile("keys/private.pem"):
            with open("keys/private.pem", "rb") as prv_file:
                try:
                    self.privateKey = RSA.importKey(self.decryptPrvKey(prv_file.read(), hash))
                except:
                    self.privateKey = RSA.generate(2048)
        else:
            self.privateKey = RSA.generate(2048)
            with open("keys/private.pem", "wb") as prv_file:
                prv_file.write(self.encryptPrvKey(self.privateKey.exportKey('PEM'), hash))

            with open("public.pem", "wb") as pub_file:
                pub_file.write(self.privateKey.publickey().exportKey('PEM'))

        if os.path.isfile("public/public.pem"):
            with open("public/public.pem", "rb") as pub_file:
                self.publicKey = RSA.importKey(pub_file.read())

        self._input = str()
        self._observers = []
        self.inBuff = fifo()
        self.outBuff = fifo()
        self.startInputBuffer()
        self.startOutputBuffer()
        self.chost, self.cport = "25.136.199.168", 5000
        self.createServer(ip, int(port))#"25.136.199.168", 5001)
        self.testCount = 0
        self.file = File()

    @property
    def input(self):
        return self._input

    @input.setter
    def input(self, value):
        self._input = value
        for callback in self._observers:
            callback(self._input)

    def bind_to(self, callback):
        self._observers.append(callback)

    def startOutputBuffer(self):
        thread = self.outputBuffer()
        thread.start()
        return thread

    @threaded.Threaded(name="outputbuffer", daemon=True)
    def outputBuffer(self):
        while True:
            if self.outBuff.empty():
                sleep(1)
            else:
                txt = self.outBuff.get(True)
                if self.file.sending and txt == self.file.outFile.name:
                    self._sendFile(self.file.outFile)
                else:
                    self._sendMessage(str(txt))

    def startInputBuffer(self):
        thread = self.inputBuffer()
        thread.start()
        return thread

    @threaded.Threaded(name="inputbuffer", daemon=True)
    def inputBuffer(self):
        while True:
            if self.inBuff.empty():
                sleep(1)
            else:
                txt = self.inBuff.get(True)
                print(len(txt))
                if self.hasKey == False:
                    tmp = self.decryptKey(txt)
                    self.dKey = tmp
                    self.hasKey = True
                elif self.file.receiving == True:
                    if len(txt) == 144 or len(txt) == 128:
                        try:
                            data = self.decryptMessage(txt)
                            if (data == "file:end:"):
                                self.receiving = False
                                self.file.file.close()
                                self.input = "Our friend finished sending file " + self.file.name
                                self.file.receiving = False
                        except:
                            if self.file.file.closed:
                                self.file.file = open('./' + str(self.file.name), 'wb')
                            data = self.decryptFile(txt)
                            self.file.file.write(data)
                    else:
                        if self.file.file.closed:
                            self.file.file = open('./' + str(self.file.name), 'wb')
                        data = self.decryptFile(txt)
                        self.file.file.write(data)
                else:
                    try:
                        data = str(self.decryptMessage(txt))
                        msg = data.split(':', maxsplit=1)
                        if (msg[0] == "file"):
                            msg = msg[1].split(':', maxsplit=1)
                            if (msg[0] == "start"):
                                msg = msg[1]
                                self.file.name = msg
                                self.file.receiving = True
                                self.file.file = open('./' + str(self.file.name), 'wb')
                                self.input = "Our friend is sending file " +self.file.name
                        elif (msg[0] == "msg"):
                            self.input = "Our friend: " + msg[1]
                    except ValueError:
                        print("I caught a fish!")
                        done = 0
                        for n in range(2, 10):
                            if done == n - 1:
                                break
                            txt0 = txt
                            l = int(len(txt0) / n)
                            for _ in range(n):
                                txt1 = txt0[:l]
                                txt0 = txt0[l:]
                                try:
                                    data = self.decryptMessage(txt1)
                                except:
                                    done = 0
                                    break
                                self.input = "Our friend: " + str(data)
                                done += 1

    def createClient(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client = s
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect((self.chost, self.cport))
        self.sendKey(self.key)



    def close(self):
        try:
            self.client.close()
            threaded._threadpooled.ThreadPooled.shutdown()
            self.hasKey = False
        except:
            print("there was no client")

    def sendKey(self, key):
        tmp = self.encryptKey(self.key)
        self.client.send(tmp)
        return None

    def sendMessage(self, message):
        self.outBuff.put(message, True)

    def _sendMessage(self, message):
        while True:
            try:
                self.client.send(self.encryptMessage("msg:"+message)) # + str(self.testCount)))
                self.testCount += 1
                break
            except ConnectionResetError:
                self.input = "Cannot reach " + str(self.chost) + ":" + str(self.cport)
                while True:
                    try:
                        self.createClient()
                        break
                    except ConnectionRefusedError:

                        sleep(1.5)
                self.input = "Connection to " + str(self.chost) + ":" + str(self.cport) + " reached!"

    def sendFile(self, file):
        self.file.outFile = file
        self.file.sending = True
        self.outBuff.put(file.name, True)


    def _sendFile(self, file):
        file.file = open(file.path, 'rb')
        load = file.file.read(512)
        file.currentSize = 512
        self.client.send(self.encryptMessage("file:start:" + str(file.name)))  # number that means sending a file
        while (load):
            self.client.send(self.encryptFile(load))
            sleep(0.001)
            load = file.file.read(512)
            self.input = "progress_bar:=" + str(int(100 * file.currentSize/file.size))
            file.currentSize += 512
        self.client.send(self.encryptMessage("file:end:"))
        file.file.close()
        self.file.sending = False

    def createServer(self, host, port):
        thread = self.server(host, port)
        thread.start()
        return thread

    @threaded.Threaded(name="server", daemon=True)
    def server(self, host, port):
        while True:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
            except socket.error as e:
                print(str(e))
            s.listen(1)

            c, addr = s.accept()
            print("Connection from: " + str(addr))

            while True:
                try:
                    data = c.recv(1024)
                except ConnectionResetError:
                    print("Connection lost </3")
                    break
                if not data:
                    break
                self.inBuff.put(data, True)
            c.close()
        pass

    def encryptPrvKey(self, data, hash):
        self.mode = AES.MODE_CBC
        self.updateAES(hash)
        cphrtxt = self.cipher.iv + self.cipher.encrypt(pad(data, 128, style='iso7816'))
        self.mode = AES.MODE_ECB
        self.updateAES(self.key)
        return cphrtxt

    def decryptPrvKey(self, data, hash):
        self.mode = AES.MODE_CBC
        self.updateAES(hash)
        if (self.cipher.iv != data[:self.cipher.block_size]):
            self.updateIV(hash, data[:self.cipher.block_size])
        txt = unpad(self.cipher.decrypt(data[self.cipher.block_size:]), 128, style='iso7816')
        self.mode = AES.MODE_ECB
        self.updateAES(self.dKey)
        return txt

    def encryptMessage(self, txt):
        if self.mode == AES.MODE_ECB:
            self.updateAES(self.key)
            return self.cipher.encrypt(pad(txt.encode(), 128, style='iso7816'))
        else:
            self.updateAES(self.key)
            return self.cipher.iv + self.cipher.encrypt(pad(txt.encode(), 128, style='iso7816'))

    def decryptMessage(self, txt):
        if self.mode == AES.MODE_ECB:
            self.updateAES(self.dKey)
            return unpad(self.cipher.decrypt(txt), 128, style='iso7816').decode()
        else:
            self.updateAES(self.dKey)
            if(self.cipher.iv != txt[:self.cipher.block_size]):
                self.updateIV(self.dKey, txt[:self.cipher.block_size])
            return (unpad(self.cipher.decrypt(txt[self.cipher.block_size:]), 128, style='iso7816')).decode()

    def encryptFile(self, data):
        if self.mode == AES.MODE_ECB:
            self.updateAES(self.key)
            return self.cipher.encrypt(pad(data, 128, style='iso7816'))
        else:
            self.updateAES(self.key)
            return self.cipher.iv + self.cipher.encrypt(pad(data, 128, style='iso7816'))

    def decryptFile(self, data):
        if self.mode == AES.MODE_ECB:
            self.updateAES(self.dKey)
            return unpad(self.cipher.decrypt(data), 128, style='iso7816')
        else:
            self.updateAES(self.dKey)
            if(self.cipher.iv != data[:self.cipher.block_size]):
                self.updateIV(self.dKey, data[:self.cipher.block_size])
            return unpad(self.cipher.decrypt(data[self.cipher.block_size:]), 128, style='iso7816')

    def updateIV(self, key, iv):
        self.cipher = AES.new(key, self.mode, iv=iv)

    def updateAES(self, key):
        self.cipher = AES.new(key, self.mode)

    def changeMode(self, m):
        if m == 'ECB':
            self.mode = AES.MODE_ECB
        elif m == 'CBC':
            self.mode = AES.MODE_CBC
        elif m == 'CFB':
            self.mode = AES.MODE_CFB
        elif m == 'OFB':
            self.mode = AES.MODE_OFB
        self.updateAES()

    def encryptKey(self, key):
        rcipher = PKCS.new(self.publicKey)
        return rcipher.encrypt(key)

    def decryptKey(self, key):
        rcipher = PKCS.new(self.privateKey)
        sentinel = Random.new().read(len(key))
        return rcipher.decrypt(key, sentinel)

def main():
    window = W.Window()
    #window.window.mainloop()


if __name__ == '__main__':
    main()
    quit()
