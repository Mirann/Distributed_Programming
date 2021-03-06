from __future__ import with_statement
from rpyc import Service, async, connect
from rpyc.utils.server import ThreadedServer
from copy import deepcopy


clients = []
my_port = 19914

class ClientToken(object):
    def __init__(self, name, update_data, mass_start, get_wait, update_information,
                 get_received_data_count):
        self.name = name
        self.stale = False
        self.wait_me = False
        self.callback_update_data = update_data
        self.callback_mass_start = mass_start
        self.callback_get_wait = get_wait
        self.callback_update_information = update_information
        self.callback_get_received_data_count = get_received_data_count
        print("* Hello %s *" % self.name)
        clients.append(self)

        print("\nAll clients:")
        for c in clients:
            print(c.name)

    def exposed_logout(self):
        if self.stale:
            return
        self.stale = True

        self.callback_update_data = None
        self.callback_mass_start = None
        self.callback_get_my_data_count = None
        self.callback_get_wait = None
        self.callback_update_information = None

        self.update_client_stale()
        print("* Goodbye %s *" % self.name)

    def update_client_stale(self):
        for c in clients:
            if c.name == self.name:
                c.stale = self.stale

    def exposed_update_data(self, count, size):
        if self.stale:
            self.update_client_stale()
            raise ValueError("User token is stale ", self.name)
        self.broadcast_update_data(count, size)

    def broadcast_update_data(self, count, size):
        for client in clients:
            try:
                if client.stale:
                    return
                client.callback_update_data(count, size)
            except:
                print("EXCEPTION broadcast_update_data ", client.name)
                client.stale = True
                self.update_client_stale()

    def exposed_mass_start(self):
        if self.stale:
            self.update_client_stale()
            raise ValueError("User token is stale ", self.name)
        self.broadcast_mass_start()

    def broadcast_mass_start(self):
        for client in clients:
            try:
                if client.stale:
                    continue
                client.callback_mass_start()
            except:
                print("EXCEPTION broadcast_mass_start ", client.name)
                client.stale = True
                self.update_client_stale()

    def exposed_update_information(self, value):
        if self.stale:
            self.update_client_stale()
            raise ValueError("User token is stale ", self.name)
        self.broadcast_update_information(value)

    def broadcast_update_information(self, value):
        for client in clients:
            try:
                if client.stale:
                    continue
                client.callback_update_information(self.name, value)
            except:
                print("\nEXCEPTION broadcast_update_information ", client.name)
                client.stale = True
                self.update_client_stale()

    def exposed_get_received_data_count(self):
        if self.stale:
            self.update_client_stale()
            raise ValueError("User token is stale ", self.name)
        return self.broadcast_get_received_data_count()

    def broadcast_get_received_data_count(self):
        count = 0
        for client in clients:
            try:
                if client.stale:
                    continue
                count += client.callback_get_received_data_count().value
            except Exception:
                print("EXCEPTION broadcast_get_received_data_count ", client.name)
                client.stale = True
                self.update_client_stale()
                continue
        return count

    def exposed_get_wait_me_clients_count(self):
        if self.stale:
            self.update_client_stale()
            raise ValueError("User token is stale ", self.name)

        count = 0
        for client in clients:
            if client.stale:
                continue
            if client.wait_me:
                count += 1
        return count

    def exposed_wait_me(self, value):
        try:
            for client in clients:
                if client.name == self.name:
                    client.wait_me = value
        except:
            print("EXCEPTION exposed_wait_me ")

    def exposed_get_active_clients_count(self):
        count = 0
        for client in clients:
            if not client.stale:
                count += 1
        return count

    def exposed_get_clients_count(self):
        return len(clients)


class RegisterService(Service):
    def on_connect(self):
        self.client = None

    def on_disconnect(self):
        if self.client:
            self.client.exposed_logout()

    def exposed_login(self, username, update_data, mass_start, get_wait, update_information,
                      get_received_data_count):
        if self.client and not self.client.stale:
            raise ValueError("already logged in")
        for client in clients:
            if client.name == username:
                return client
        else:
            self.client = ClientToken(username, async(update_data), async(mass_start),
                                      get_wait, async(update_information), async(get_received_data_count))
            return self.client


if __name__ == "__main__":
    t = ThreadedServer(RegisterService, port=my_port)
    t.start()

