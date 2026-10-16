from memory import MemoryStore, SecretDetected, MemoryNotFound

HELP = """Commands:
  remember <text>       store an event
  fact <text>           store a fact about you
  recall <question>     find related memories
  list                  show the 10 latest memories
  edit <id> <new text>  correct a memory
  forget <id>           delete a memory permanently
  log                   show the audit log
  help | quit"""

SURE = 0.40  # tuned with eval_recall.py; between min_score (0.30) and this: "not sure"


def main():
    print("Loading KORA's memory (first run downloads the model)...")
    store = MemoryStore("kora.db")
    print("KORA online. Type 'help'.")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        cmd, _, arg = line.partition(" ")
        cmd, arg = cmd.lower(), arg.strip()

        try:
            if cmd in ("quit", "exit"):
                break
            elif cmd == "help":
                print(HELP)
            elif cmd in ("remember", "fact"):
                if not arg:
                    print("Remember what?")
                    continue
                mid = store.add(arg, kind="event" if cmd == "remember" else "fact")
                print(f"Stored as #{mid}.")
            elif cmd == "recall":
                results = store.recall(arg)
                if not results:
                    print("I don't know. Nothing in memory looks related.")
                    continue
                if results[0][1] < SURE:
                    print("I'm not sure, but these might be related:")
                for m, score in results:
                    print(f"  #{m['id']} [{score:.2f}] {m['created_at'][:10]} ({m['kind']}) {m['text']}")
            elif cmd == "list":
                for m in store.latest():
                    print(f"  #{m['id']} {m['created_at'][:16]} ({m['kind']}) {m['text']}")
            elif cmd == "edit":
                mid, _, text = arg.partition(" ")
                store.edit(int(mid), text)
                print(f"Memory #{mid} corrected.")
            elif cmd == "forget":
                store.forget(int(arg))
                print(f"Memory #{arg} deleted.")
            elif cmd == "log":
                for e in store.audit():
                    print(f"  {e['at']}  {e['action']:<16} #{e['memory_id']}  {e['detail'] or ''}")
            else:
                print("Unknown command. Type 'help'.")
        except SecretDetected:
            print("That looks like a secret (password, key or token). I won't store it.")
        except MemoryNotFound as e:
            print(e)
        except ValueError:
            print("The id must be a number, e.g. 'forget 3'.")


if __name__ == "__main__":
    main()