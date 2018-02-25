defmodule Client do
  def start do
    host = "localhost"
    port = 9999
    sock = Socket.TCP.connect! host, port
  end
end

Client.start()
require IEx
IEx.pry
