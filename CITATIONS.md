# Citations (owned by Isha; one place for the whole deck)

**Before anything goes on a slide: open every link marked ⚠️ yourself.** Those are preprints or 2026 items, or details that came from our research doc and haven't been checked against the source.

## Used directly in the presets (source comments in `specs/*.yaml`)

| Where | Reference |
|---|---|
| banks J | Elliott, M., Golub, B. & Jackson, M. O. (2014). Financial Networks and Contagion. *American Economic Review* 104(10), 3115–3153. Dependency matrix A = Ĉ(I−C)⁻¹. |
| banks J (Ising mapping), bailout field | ⚠️ Tomar, Nagpal, Chauhan & Hassan (2026). Financial Contagion Networks as Annealing-Ready Ising Systems. arXiv:2609.17415 (**preprint, not peer-reviewed**). |
| banks topology | Craig, B. & von Peter, G. (2014). Interbank tiering and money center banks. *Journal of Financial Intermediation* 23(3), 322–347. |
| banks h | Basel Committee on Banking Supervision (2010, rev. 2011). Basel III: A global regulatory framework for more resilient banks and banking systems. 4.5% CET1 minimum + 2.5% conservation buffer. |
| firms J | Cooper, R. & John, A. (1988). Coordinating Coordination Failures in Keynesian Models. *Quarterly Journal of Economics* 103(3), 441–463. |
| firms J | ⚠️ Ball, L. & Romer, D. (1991). Sticky Prices as Coordination Failure. *American Economic Review* 81(3), 539–552. |
| firms disorder (RFIM) | Bouchaud, J.-P. (2013). Crises and collective socio-economic phenomena: simple models and challenges. *J. Stat. Phys.* 151, 567–606. arXiv:1209.0453. |
| taxpayers | ⚠️ Zaklan, G., Westerhoff, F. & Stauffer, D. (2009). Analysing tax evasion dynamics via the Ising model. *J. Economic Interaction and Coordination* 4, 1–14. |

## Background / framing

| Topic | Reference |
|---|---|
| Ising ↔ logit bridge, review | Sornette, D. (2014). Physics and Financial Economics (1776–2014). arXiv:1404.0243. |
| spin market model | Bornholdt, S. (2001). Expectation bubbles in a spin model of markets. *Int. J. Mod. Phys. C* 12, 667–674. |
| crashes | Krawiecki, A. & Hołyst, J. A. (2003). *Physica A* 317, 597–608. |
| Hamiltonian finance | Baaquie, B. E. (2004). *Quantum Finance*. Cambridge University Press. (Mostly imaginary-time / classical stochastic processes in quantum notation.) |
| quantum decision theory | Yukalov, V. I. & Sornette, D. (2011). Decision theory with prospect interference and entanglement. *Theory and Decision* 70, 283–328. |
| quantum cognition | Pothos, E. M. & Busemeyer, J. R. (2009). *Proc. R. Soc. B* 276, 2171–2178. Pothos & Busemeyer (2022). Quantum Cognition. *Annual Review of Psychology* 73, 749–778. |
| order effects | Trueblood, J. S. & Busemeyer, J. R. (2011). *Cognitive Science* 35(8), 1518–1552. |
| critique | Boyer-Kassem, T., Duchêne, S. & Guerci, E. (2016). *Mathematical Social Sciences* 80, 33–46; and *Theory and Decision* 81(4), 479–510. |
| quantum games | Eisert, Wilkens & Lewenstein (1999). *PRL* 83, 3077. Li, Du & Massar (2002). *Phys. Lett. A* 306, 73. |

## Quantum simulation (Shiven's slides)

| Topic | Reference |
|---|---|
| idea | Feynman, R. P. (1982). Simulating physics with computers. *Int. J. Theor. Phys.* 21, 467–488. |
| Trotter simulation | Lloyd, S. (1996). Universal Quantum Simulators. *Science* 273, 1073–1078. |
| Trotter error | Childs, Su, Tran, Wiebe & Zhu (2021). Theory of Trotter Error with Commutator Scaling. *PRX* 11, 011020. |
| 127-qubit kicked Ising | Kim et al. (2023). Evidence for the utility of quantum computing before fault tolerance. *Nature* 618, 500–505. |
| classical rebuttals | Tindall et al. (2024). *PRX Quantum* 5, 010308. Begušić & Chan (2024). *Science Advances* 10, eadk4321. |

## Software

Qiskit 2.6.2 (`SparsePauliOp`, `PauliEvolutionGate`, `SuzukiTrotter`, `StatevectorEstimator`), SciPy `expm_multiply`, NetworkX. qiskit-finance is archived and **not** used.
