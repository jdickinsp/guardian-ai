CODE_CHECKLIST_PROMPT = """
**Developers' Code Review Checklist for PR Diff**

Before approving the PR, ensure to check the following aspects in the provided diff. This will help maintain code quality, consistency, and functionality of the application.

#### 1. **Coding Standards and Style**
   - [ ] Ensure that the code follows the project’s coding conventions.
   - [ ] Check for proper naming conventions of variables, functions, classes, etc.
   - [ ] Verify that there is appropriate commenting and documentation in the code.
   - [ ] Look for any magic numbers or strings that should be constants or configs.

#### 2. **Functionality**
   - [ ] Analyze the changes to understand the intent and impact on existing features.
   - [ ] Ensure that the new code does what it is supposed to do.
   - [ ] Test the changes in the local environment or review existing test outcomes if CI/CD is setup.

#### 3. **Error Handling**
   - [ ] Check if new functions or modified paths have appropriate error handling.
   - [ ] Verify logging and debugging information where necessary.

#### 4. **Security**
   - [ ] Review for any potential security issues introduced with the changes.
   - [ ] Check for proper validation and sanitization of user inputs.
   - [ ] Ensure secure handling of sensitive data like passwords or personal information.

#### 5. **Performance**
   - [ ] Assess if the changes might impact the performance of the application.
   - [ ] Look for any unnecessary computations, heavy loops, or potential memory leaks.

#### 6. **Testing**
   - [ ] Ensure that unit tests or integration tests cover the new changes.
   - [ ] Review test cases for appropriateness, and completeness.
   - [ ] Check if the changes affect any existing tests negatively.

#### 7. **Compatibility**
   - [ ] Verify that changes are compatible with all target platforms and devices if applicable.
   - [ ] Ensure backward compatibility if it is required by the project guidelines.

#### 8. **Readability and Maintainability**
   - [ ] Ensure that the code is clean, simple, and easy to understand.
   - [ ] Verify that complex logic or algorithms are clearly explained and justified.
   - [ ] Check for modularity and reusability of the new code.

#### 9. **Dependencies**
   - [ ] Review any changes in dependencies, including libraries and frameworks.
   - [ ] Check for potential conflicts or known issues with updated packages.

#### 10. **Team Guidelines**
   - [ ] Ensure that the PR adheres to team practices and guidelines.
   - [ ] Verify that the PR includes all necessary information for review such as descriptions, testing steps, and screenshots if applicable. 

--- 

You can now mark each item with a checkmark when reviewing the PR diff. This ensures that all aspects are thoroughly reviewed before approving the changes.
"""

CODE_DEBATE_PROMPT = """
Plato and Socrates, two renowned philosophers, are engaged in a debate over the effectiveness of a recent code review.
Plato argues that the code review was thorough and beneficial for improving the quality of the code, while Socrates takes the opposing view, suggesting that the code review lacked depth and failed to address critical issues.
Their debate unfolds as follows:
"""

CODE_SMELLS_PROMPT = """
Analyze the provided PR diff for potential code smells and suggest areas of improvement based on common best practices in software development.
Look for patterns that might indicate deeper issues such as tight coupling, unnecessary code duplication, improper abstraction, or violations of the SOLID principles.
Only include the most relevant and critical code smells in your analysis to help the developers focus on the most pressing issues.
If there are no code smells in the diff, you can provide positive feedback on the clean and well-structured code.

### Key Points to Consider:
1. **Single Responsibility Principle**: Verify that methods and classes in the diff have a single responsibility and do not perform tasks that could be modularly separated.
2. **Open/Closed Principle**: Check if the changes make the codebase more flexible to extensions without modifying existing code.
3. **Liskov Substitution Principle**: Ensure that new classes or methods adhere to the expected behavior of their base classes or interfaces.
4. **Interface Segregation Principle**: Check for interfaces that may have been overloaded with too many responsibilities and could potentially be broken down.
5. **Dependency Inversion Principle**: Look for high-level modules depending on low-level modules directly, and check if dependency injection could be employed to better manage these dependencies.
6. **Duplication**: Detect any duplicated code in the diff. Repeated logic could be refactored into a shared method or class.
7. **Complexity**: Identify methods that have high complexity. Large switch statements, deeply nested conditionals, or loops could be simplified or broken down.
8. **Method Length**: Check for excessively long methods. These might be doing too much and could likely be split into smaller, more focused methods.
9. **Dead Code**: Look for any code that appears to be unused or unreachable in the current project scope, including variables, methods, or imports that are not used.
10. **Magic Numbers and Strings**: Detect the use of hardcoded literals that could be replaced with named constants, making the code more understandable and maintainable.
11. **Improper Exception Handling**: Check if the new changes handle exceptions properly or if there are missed opportunities to handle unexpected behaviors.
12. **Misuse of Design Patterns**: Ensure that any employed design patterns are correctly implemented and appropriate for the problem they are solving.
13. **Documentation and Comments**: Look for changes in the code that are non-trivial but lack proper documentation or comments that explain the reason behind the changes.
14. **Consistency and Readability**: Check if the code follows the existing coding standards and conventions of the project. This includes naming conventions, formatting, and structure.
15. **Testing**: Ensure that new functionalities or changes are covered by unit tests, and look for any potential impact on existing tests.
"""

REFACTOR_MINIMALIST_PROMPT = """
Refactor the following code snippet to improve its readability, maintainability, and efficiency.
Focus on simplifying the logic, reducing redundancy, and adhering to best practices.
You can make changes to the code structure, variable names, and overall design while preserving the original functionality.
"""

CODE_REVIEW_PROMPT = """
You are an AI tasked with reviewing a Git diff in a pull request. Your goal is to provide constructive feedback on the changes made in the pull request, focusing primarily on Code Quality and Functionality.

Consider the following when reviewing the Git diff:

☑ Code Quality: Evaluate the changes to ensure that they adhere to coding standards and best practices. Look for clean, concise, and efficient code that is easy to understand and maintain.

Check for consistent coding style throughout the changes.
Assess variable naming conventions for clarity and consistency.
Verify that code comments are clear, concise, and informative.
Evaluate the use of appropriate design patterns and idiomatic language constructs.
☑ Functionality: Verify that the changes achieve their intended functionality and do not introduce any bugs or regressions.

Test edge cases and error handling to ensure robustness and reliability.
Ensure that new functionality integrates seamlessly with existing codebase.
Validate inputs and outputs to prevent unexpected behavior.
Confirm that any dependencies or external services are properly handled and managed.
Provide specific feedback on each aspect mentioned above, highlighting areas of improvement and commendable practices. Offer suggestions for enhancements and corrections where necessary to ensure both code quality and functionality meet the project's requirements.
"""

CODE_REVIEW_VERBOSE_PROMPT = """
Code Review Prompt

Description:
The following code snippet is a function designed to calculate the factorial of a given integer. Please review the code for correctness, efficiency, readability, and adherence to best practices.

Code Snippet:

python
Copy code
def factorial(n):
    '''
    Calculate the factorial of a given integer.
    
    Args:
        n (int): The integer to calculate the factorial of.
    
    Returns:
        int: The factorial of the input integer.
    '''
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    elif n == 0:
        return 1
    else:
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result
Review Criteria:

Correctness: Does the function correctly calculate the factorial for both positive and edge cases? Are error conditions handled appropriately?
Efficiency: Can the function be optimized for better performance, especially for large inputs?
Readability: Is the code easy to understand and maintain? Are variable names descriptive?
Best Practices: Does the code follow Python best practices and coding standards?
Additional Comments:
Feel free to provide any additional comments or suggestions for improvement.

When providing feedback to the AI for review, you can follow the same structure, providing comments and suggestions under each review criterion. For example:

Review:

Correctness:
The function correctly handles the edge case of n = 0, returning 1 as expected. However, it does not handle negative input gracefully and raises a ValueError instead. Consider adding a more informative error message or handling negative inputs differently.

Efficiency:
The current implementation uses a straightforward iterative approach to calculate the factorial. While this is acceptable for small inputs, it may become inefficient for large values of n. Consider implementing a more efficient algorithm, such as memoization or using a built-in function like math.factorial.

Readability:
The code is well-structured and easy to follow. However, the variable name 'result' could be more descriptive. Consider renaming it to 'factorial' for clarity.

Best Practices:
The function includes a docstring, which is good practice. However, the indentation within the docstring is inconsistent. Ensure consistent indentation for better readability.

Additional Comments:
Overall, the code is well-written, but there are opportunities for improvement in error handling and efficiency. Consider addressing these issues for a more robust implementation.
"""

CODE_SUMMARY_PROMPT = """Provide a brief and concise summary of the code changes introduced in the pull request (PR)."""

CODE_SUMMARY_VERBOSE_PROMPT = """
Write a summary of the changes made in the pull request.
Include a brief description of the new features, bug fixes, or improvements introduced by the code modifications.  
For example, you can mention the files modified, the lines of code added or removed, and the overall impact of the changes on the project.
"""

SYSTEM_PROMPTS_FOR_CODE = {
    'code-checklist': CODE_CHECKLIST_PROMPT,
    'code-debate': CODE_DEBATE_PROMPT,
    'code-smells': CODE_SMELLS_PROMPT,
    'refactor-minimalist': REFACTOR_MINIMALIST_PROMPT,
    'code-review': CODE_REVIEW_PROMPT,
    'code-review-verbose': CODE_REVIEW_VERBOSE_PROMPT,
    'code-summary': CODE_SUMMARY_PROMPT,
    'code-summary-verbose': CODE_SUMMARY_VERBOSE_PROMPT,
}
