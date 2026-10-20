// Deep template recursion compile bomb
template <int N>
struct Recursive {
    enum { val = Recursive<N - 1>::val + Recursive<N - 2>::val };
};

template <>
struct Recursive<0> {
    enum { val = 1 };
};

template <>
struct Recursive<1> {
    enum { val = 1 };
};

int main() {
    return Recursive<10000>::val;
}
