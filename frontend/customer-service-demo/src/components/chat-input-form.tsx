import { Send } from "lucide-react";
import { useState } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

interface ChatInputFormProps {
  onSubmit: (message: string) => void;
  isLoading: boolean;
  isEmpty: boolean;
}
const ChatInputForm = (props: ChatInputFormProps) => {
  const [message, setMessage] = useState("");

  if (props.isEmpty) {
    return (
      <div className="w-full">
        <Button
          variant="outline"
          className="w-full"
          onClick={() => props.onSubmit("Hello customer service")}
        >
          Start conversation
        </Button>
      </div>
    );
  }

  return (
    <form
      className="w-full relative flex items-center"
      onSubmit={(e) => {
        e.preventDefault();
        props.onSubmit(message);
        setMessage("");
      }}
    >
      <Input
        value={message}
        onChange={(e) => {
          setMessage(e.target.value);
        }}
        placeholder="Type your message..."
        disabled={props.isLoading}
        className="pr-10"
      />
      <Button
        variant="default"
        size={"icon"}
        className="absolute right-1 size-7"
        disabled={!message.trim() || props.isLoading}
        type="submit"
      >
        <Send />
      </Button>
    </form>
  );
};

export default ChatInputForm;
