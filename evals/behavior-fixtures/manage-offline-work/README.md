# Messaging Core

The messaging core supports offline message deletion by marking a message `pending_delete` until the
server confirms it. Threads currently belong to the source message and synchronize independently.
