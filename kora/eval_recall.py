from memory import MemoryStore

# Fake but realistic memories; each question below uses different words on purpose.
MEMORIES = [
    "My systems design exam is on 3 November",
    "I prefer Flutter for mobile and React for web",
    "I deployed the attendance app on Contabo with Docker on Monday",
    "My Contabo server has 4 vCPUs and about 8 GB of RAM",
    "I added 4 GB of swap to the server",
    "MySQL port 3306 is still open on the server firewall",
    "I study at ICT University in Yaounde",
    "I built a neural network from scratch that recognises noisy digits",
    "My Dyna-Q agent learned that the door needs a key",
    "I usually study late at night after 10 pm",
    "My laptop is an HP ProBook with a weak MX250 graphics card",
    "I drink coffee every morning before classes",
    "My group project presentation is next Friday",
    "Jenkins runs the CI pipeline for my projects",
    "I want KORA to always ask before deleting files",
]

# (question, index in MEMORIES of the memory that answers it)
RELATED = [
    ("What date is my exam?", 0),
    ("Which framework do I use for phone apps?", 1),
    ("What do I build websites with?", 1),
    ("Where is the attendance system hosted?", 2),
    ("How much memory does my VPS have?", 3),
    ("Did I configure swap space?", 4),
    ("Is the database port exposed to the internet?", 5),
    ("Which university do I attend?", 6),
    ("Where do I go to school?", 6),
    ("Have I ever coded backpropagation by hand?", 7),
    ("What did my reinforcement learning agent discover?", 8),
    ("When do I usually do my coursework?", 9),
    ("What GPU does my computer have?", 10),
    ("What do I do every morning?", 11),
    ("When do we present the team project?", 12),
    ("What tool handles continuous integration?", 13),
    ("What should KORA do before removing a file?", 14),
]

# Nothing in memory answers these. The last four are personal on purpose: the hardest case.
UNRELATED = [
    "What is the capital of Peru?",
    "How tall is Mount Kilimanjaro?",
    "Who won the 2010 World Cup?",
    "What is the boiling point of water?",
    "How do I cook ndole?",
    "What's the weather tomorrow?",
    "What is my favourite movie?",
    "Do I have a cat?",
    "What is my mother's name?",
    "Which bus do I take to the airport?",
]

THRESHOLDS = [t / 100 for t in range(20, 70, 5)]


def top_match(store, question):
    memory, score = store.recall(question, k=1, min_score=-1.0)[0]
    return memory, score


def main():
    store = MemoryStore(":memory:")  # throwaway database: kora.db is not touched
    ids = [store.add(text) for text in MEMORIES]

    print("\nRelated questions (should find the right memory):")
    related = []
    for question, index in RELATED:
        memory, score = top_match(store, question)
        correct = memory["id"] == ids[index]
        related.append((correct, score))
        print(f"  {'right' if correct else 'WRONG'}  {score:.2f}  {question}")

    print("\nUnrelated questions (should get 'I don't know'):")
    unrelated = []
    for question in UNRELATED:
        memory, score = top_match(store, question)
        unrelated.append(score)
        print(f"  {score:.2f}  {question}  -> closest: {memory['text']}")

    print("\nthreshold  right  wrong  dont-know  false-alarms")
    rows = []
    for t in THRESHOLDS:
        right = sum(c and s >= t for c, s in related)
        wrong = sum(not c and s >= t for c, s in related)
        dont_know = sum(s < t for _, s in related)
        false_alarms = sum(s >= t for s in unrelated)
        rows.append((t, right, wrong, false_alarms))
        print(f"  {t:.2f}     {right:>2}/{len(related)}    {wrong:>2}      {dont_know:>2}         {false_alarms:>2}/{len(unrelated)}")

    # A confident wrong answer costs twice as much as an honest "I don't know"; ties go to the stricter threshold.
    best = max(rows, key=lambda r: (r[1] - 2 * (r[2] + r[3]), r[0]))
    safe = next((r for r in rows if r[2] == 0 and r[3] == 0), None)
    print(f"\nSuggested min_score (answer at all):     {best[0]:.2f}")
    print(f"Suggested SURE (answer confidently):     {safe[0]:.2f}" if safe else "No threshold had zero mistakes.")


if __name__ == "__main__":
    main()
