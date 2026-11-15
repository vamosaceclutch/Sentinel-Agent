// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Hand-written fix of VulnerableVault, used as the "after" in the demo.
/// What changed and why:
///  - withdraw(): state is updated BEFORE the external call (checks-effects-interactions)
///    and a reentrancy guard blocks a second entry.
///  - emergencyWithdraw() and setOwner() are removed: they let anyone drain the vault
///    or take it over, and a vault that holds user funds does not need them.
contract FixedVault {
    mapping(address => uint256) public balances;
    bool private locked;

    modifier nonReentrant() {
        require(!locked, "reentrant call");
        locked = true;
        _;
        locked = false;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external nonReentrant {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "nothing to withdraw");
        balances[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }
}
